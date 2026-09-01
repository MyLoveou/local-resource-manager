# 02 · Electron 后端子进程编排（services 模块）

## 职责

主进程在 `app.whenReady()` 时拉起 uvicorn 后端，就绪后注入地址，退出时清理——让渲染进程永远不用关心后端怎么活。

```
src/main/infrastructure/services/
├── index.ts    # 编排：startServices / stopServices
├── backend.ts  # spawn uvicorn + 健康检查 + 停止
├── port.ts     # 找空闲端口
└── config.ts   # 静态配置（路径/超时）
```

## 核心代码

### port.ts —— 找空闲端口

```ts
import { createServer } from 'net'
import type { AddressInfo } from 'net'

export function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer()
    srv.listen(0, '127.0.0.1', () => {
      const port = (srv.address() as AddressInfo).port
      srv.close(() => resolve(port))   // 必须 resolve（踩坑见 08）
    })
    srv.on('error', reject)
  })
}
```

### config.ts —— 静态配置，env 优先，动态值不入配置

```ts
function resolveProjectRoot(): string {
  // dev: app.getAppPath() = apps/desktop → 上两级即仓库根
  return process.env.PROJECT_ROOT ?? resolve(app.getAppPath(), '../..')
}

function defaultPythonPath(root: string): string {
  return process.platform === 'win32'
    ? join(root, 'apps/backend/.venv/Scripts/python.exe')   // .venv 非 .env
    : join(root, 'apps/backend/.venv/bin/python')
}
// BACKEND_PYTHON_PATH / BACKEND_DIR / BACKEND_MODULE / BACKEND_HOST / 超时 均可 env 覆盖
```

### backend.ts —— spawn + 健康检查

```ts
export async function startBackend(cfg: BackendConfig): Promise<BackendInstance> {
  const port = await getFreePort()
  const token = randomBytes(16).toString('hex')
  const child = spawn(cfg.pythonPath,
    ['-m', 'uvicorn', cfg.module, '--host', cfg.host, '--port', String(port)],
    { cwd: cfg.backendDir, env: { ...process.env, BACKEND_TOKEN: token },
      stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })

  child.stdout?.on('data', d => console.log(`[backend] ${d}`))
  child.stderr?.on('data', d => console.error(`[backend] ${d}`))
  child.once('error', reject)                      // python 不存在等 spawn 失败

  const baseUrl = `http://${cfg.host}:${port}`
  await waitForHealth(`${baseUrl}/health`, cfg.healthTimeoutMs, cfg.healthIntervalMs)
  return { baseURL: baseUrl, port, token, stop: () => killProcess(child) }
}
```

`waitForHealth`：成功条件 = 返回 **200**；网络错误/非 200 → 按 interval 重试；超时 reject（完整版见 09）。

### index.ts —— 编排

```ts
let backend: BackendInstance | null = null

export async function startServices(): Promise<BackendInstance> {
  backend = await startBackend(loadBackendConfig())
  process.env.BACKEND_URL = backend.baseURL
  process.env.BACKEND_TOKEN = backend.token
  return backend
}

export async function stopServices(): Promise<void> {
  if (backend) { await backend.stop(); backend = null }
}
```

### main/index.ts —— 接线（时序关键）

```ts
app.whenReady().then(async () => {
  const backend = await startServices()   // ① 先起后端
  backendUrl = backend.baseURL            // ② 存地址
  backendToken = backend.token
  createWindow()                          // ③ 后建窗（见 03）
})
app.on('will-quit', () => { void stopServices() })  // ④ 退出清理
```

## 关键原则

1. **先起后端、后建窗口**——窗口加载即执行 preload，读不到地址就用兜底。
2. **静态/动态分离**：config 只放路径、超时等静态项；端口、token 是运行时产物，不进配置。
3. **进程清理必须做**：`will-quit` 杀子进程，否则残留 python 进程（Windows 上尤其）。
4. **spawn 要监听 `error`**：python 路径不存在时不会抛同步错误，而是触发 `error` 事件，不监听就静默失败/崩溃。
