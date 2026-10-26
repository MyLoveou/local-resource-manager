# 02 · Electron 后端子进程编排（2026-10-19 现状）

> 目标：让渲染进程永远不用关心“后端怎么启动、端口是多少、进程死了怎么办”。
> 代码：`apps/desktop/src/main/infrastructure/services/`、`apps/desktop/src/main/index.ts`。

## 1. 模块职责

```text
src/main/infrastructure/services/
├─ index.ts    startServices / stopServices，保存唯一实例
├─ backend.ts  spawn + 健康检查 + 退出监听 + 停止
├─ port.ts     让系统分配空闲端口
└─ config.ts   dev/frozen 路径、host、超时
```

## 2. 两种运行模式

| 模式 | 条件 | 启动命令 | 数据库 |
|------|------|----------|--------|
| dev | `app.isPackaged === false` | `.venv` 里的 `python -m uvicorn app.main:app` | `apps/backend/data/library.db` |
| frozen | `app.isPackaged === true` | `resources/backend/source-manager-backend.exe` | `%APPDATA%/local-resource-manager/library.db` |

`config.ts`：

```ts
if (app.isPackaged) {
  return {
    mode: 'frozen',
    backendExe: process.env.BACKEND_EXE
      ?? join(process.resourcesPath, 'backend', 'source-manager-backend.exe'),
    ...common,
  }
}
const root = resolveProjectRoot()
return {
  mode: 'dev',
  pythonPath: process.env.BACKEND_PYTHON_PATH ?? defaultPythonPath(root),
  backendDir: process.env.BACKEND_DIR ?? join(root, 'apps/backend'),
  module: process.env.BACKEND_MODULE ?? 'app.main:app',
  ...common,
}
```

注意：

- 项目根用 `app.getAppPath()` 推导，不用 `__dirname`。开发态 `app.getAppPath()` 指向 `apps/desktop`，上两级才是仓库根。
- Windows 是 `.venv/Scripts/python.exe`，macOS/Linux 是 `.venv/bin/python`。
- 端口、token 是运行时产物，不放进静态配置。

## 3. 启动顺序

`main/index.ts`：

```ts
app.whenReady().then(async () => {
  registerDialogIpc()
  registerShellOpenIpc()
  registerThemeCssIpc()
  registerUpdateIpc()

  try {
    const backend = await startServices()
    backendUrl = backend.baseURL
    backendToken = backend.token
    backend.watchExit(() => {
      log.error('[main] backend exited unexpectedly')
      broadcastNotify(BACKEND_STOPPED)
    })
    createWindow()
    initUpdater()
  } catch (err) {
    log.error('[main] failed to start', err)
    createWindow()
    initUpdater()
    broadcastNotify(BACKEND_FAILED)
  }
})
```

顺序原因：

1. **先起后端**：创建窗口时要把地址/token 放进 `additionalArguments`。
2. **先注册 IPC**：窗口加载后可能立刻调用对话框、外链、更新。
3. **失败也建窗口**：至少能看到错误通知和日志，不是黑屏。
4. **退出清理**：

```ts
app.on('will-quit', () => {
  void stopServices()
})
```

## 4. spawn 与健康检查

`backend.ts` 的关键步骤：

```ts
const port = await getFreePort()
const token = randomBytes(16).toString('hex')

const child = spawn(command, args, {
  cwd,
  env: {
    ...process.env,
    BACKEND_TOKEN: token,
    BACKEND_VERSION: app.getVersion(),
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
    ...(cfg.mode === 'frozen'
      ? {
          BACKEND_DB_PATH: join(app.getPath('userData'), 'library.db'),
          FFPROBE_BIN: join(process.resourcesPath, 'ffprobe', 'ffprobe.exe'),
        }
      : {}),
  },
  stdio: ['ignore', 'pipe', 'pipe'],
  windowsHide: true,
})
```

### 4.1 必须同时处理三种失败

```ts
const spawnFailed = new Promise<never>((_, reject) => {
  child.once('error', reject)
})
const ready = waitForHealth(`${baseUrl}/health`, timeoutMs, intervalMs)

try {
  await Promise.race([ready, spawnFailed])
} catch (err) {
  void killProcess(child)
  throw err
}
```

- `spawn` 找不到可执行文件：走 `error` 事件，不会同步 throw。
- 进程启动了但 health 一直不通：超时 reject。
- health 先通、进程随后退出：由 `watchExit` 通知主进程。

### 4.2 健康检查的“三件套”

```ts
const req = http.get(url, (res) => {
  res.resume()
  if (res.statusCode === 200) resolve()
  else retry(timer)
})
req.on('error', () => retry(timer))
req.setTimeout(intervalMs, () => {
  req.destroy()
  retry(timer)
})
```

- 只认 **200**；
- 连接拒绝/超时都重试；
- 有总 deadline，不能无限等。

### 4.3 停止

```ts
function killProcess(child: ChildProcess): Promise<void> {
  return new Promise((resolve) => {
    if (child.exitCode !== null || child.killed) {
      resolve()
      return
    }
    child.once('exit', () => resolve())
    child.kill()
  })
}
```

Windows 下子进程清理不干净会留下 `python.exe`/后端 exe。`will-quit` 必须等 `exit`，不能只调用 `kill()` 就退出。

## 5. 为什么 `process.env` 不够

主进程设置：

```ts
process.env.BACKEND_URL = backend.baseURL
```

但渲染进程是独立 Chromium 进程，不能可靠读到主进程后来修改的 `process.env`。所以窗口创建时注入：

```ts
additionalArguments: [
  `--backend-url=${backendUrl}`,
  `--backend-token=${backendToken}`,
]
```

preload 从 `process.argv` 解析：

```ts
function readArg(name: string): string | undefined {
  const prefix = `--${name}=`
  const arg = process.argv.find((a) => a.startsWith(prefix))
  return arg?.slice(prefix.length)
}
```

详见 [03-主进程传参additionalArguments.md](03-主进程传参additionalArguments.md)。

## 6. 后端进程死了怎么办

`BackendInstance.watchExit` 允许主进程注册回调：

```ts
backend.watchExit(() => {
  log.error('[main] backend exited unexpectedly')
  broadcastNotify(BACKEND_STOPPED)
})
```

当前策略是 **提示用户重启**，不自动拉起。自动重启需要处理：

- 连续崩溃循环；
- 端口释放；
- 数据库锁；
- 用户正在进行的导入/抓取任务。

这些是后续增强项，不是当前行为。

## 7. 关键原则

1. **先后端、后窗口**，否则 preload 拿不到地址。
2. **失败也建窗口**，让错误可见。
3. **spawn 必须监听 error**。
4. **health 必须轮询、校验 200、设超时**。
5. **token 随机生成，不进日志/URL**。
6. **退出必须等子进程 exit**。
7. **dev/frozen 路径分开**，不要假设用户有 Python。

## 8. 排障顺序

```text
窗口黑屏/后端不可用
  → 看 main.log 是否有 [main] backend ready
  → 看 backend.log 是否有启动错误
  → 检查 .venv/python 或 resources/backend/*.exe
  → 检查端口是否被占用
  → 检查 /health 是否 200
  → 检查 token 是否注入到 preload
```

常见现象：

| 现象 | 根因 |
|------|------|
| `spawn ENOENT` | python/exe 路径错 |
| 端口固定 8000 冲突 | 没有用 `getFreePort` |
| 启动即 `Network Error` | 后端未就绪/窗口先加载 |
| 退出后残留 python | 未等 `exit` 或未调 `stopServices` |
| 生产环境找不到后端 | `extraResources`/`resourcesPath` 配置错 |

## 9. 延伸阅读

- [01-架构全景.md](01-架构全景.md)
- [03-主进程传参additionalArguments.md](03-主进程传参additionalArguments.md)
- [09-踩坑-健康检查未就绪崩溃.md](09-踩坑-健康检查未就绪崩溃.md)
- [10-踩坑-后端路径配置错误.md](10-踩坑-后端路径配置错误.md)
- [24-桌面端分层与模块封装.md](24-桌面端分层与模块封装.md)
- [26-发布构建与测试门禁.md](26-发布构建与测试门禁.md)

## 扩展阅读

### 站内（本仓）

- [03-主进程传参additionalArguments](03-主进程传参additionalArguments.md)
- [17-踩坑-process.env跨进程](17-踩坑-process.env跨进程.md)
- [31-踩坑-桌面端拉起后端的进程环境](31-踩坑-桌面端拉起后端的进程环境.md)
- [48-图解-启动时序与发布流水线](48-图解-启动时序与发布流水线.md)

### 站外知识

- [Electron · 进程模型](https://www.electronjs.org/docs/latest/tutorial/process-model)
- [Uvicorn](https://www.uvicorn.org/)
- [PyInstaller](https://pyinstaller.org/en/stable/)
