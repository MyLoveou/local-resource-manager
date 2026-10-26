# 17 · 踩坑：process.env 跨进程

> 本文补记早期缺失的“env 跨进程”踩坑。当前正确做法已收敛到
> [03-主进程传参additionalArguments.md](03-主进程传参additionalArguments.md)。

## 1. 现象

主进程启动后端后设置：

```ts
process.env.BACKEND_URL = backend.baseURL
process.env.BACKEND_TOKEN = backend.token
```

然后在渲染进程里读：

```ts
const baseUrl = process.env.BACKEND_URL
```

结果：

- 开发态有时读到，有时是 `undefined`；
- 打包后大概率是默认值 `http://127.0.0.1:8000`；
- token 为空，请求 401。

## 2. 根因

Electron 的渲染进程是独立 Chromium 进程，不是主进程的一个线程。

- 主进程后来改的 `process.env` 不会可靠同步到已存在的渲染进程；
- `contextIsolation: true` 时，渲染进程也没有 Node 的 `process`；
- preload 能读 `process.argv`，但不保证能读到主进程运行期修改的 env。

**结论：不要用 `process.env` 传递运行期动态值（端口、token）。**

## 3. 正确做法

主进程创建窗口时，把值作为命令行参数注入：

```ts
additionalArguments: [
  `--backend-url=${backendUrl}`,
  `--backend-token=${backendToken}`,
]
```

preload 解析：

```ts
function readArg(name: string): string | undefined {
  const prefix = `--${name}=`
  const arg = process.argv.find((a) => a.startsWith(prefix))
  return arg?.slice(prefix.length)
}
```

通过 `contextBridge` 暴露给渲染进程：

```ts
contextBridge.exposeInMainWorld('electron', {
  backend: {
    baseUrl: readArg('backend-url') ?? process.env.BACKEND_URL ?? 'http://127.0.0.1:8000',
    token: readArg('backend-token') ?? process.env.BACKEND_TOKEN ?? '',
  },
})
```

渲染层只读 `window.electron.backend`，不再读 `process.env`。

## 4. 为什么不用 IPC

也可以：

```text
preload → ipcRenderer.invoke('get-backend')
main    → ipcMain.handle('get-backend', () => ({ baseUrl, token }))
```

但：

- 多一次异步；
- 窗口创建时更容易出现时序问题；
- 地址/token 是创建窗口前就确定的静态快照，`additionalArguments` 更直接。

如果以后要支持“运行中切换后端”，再考虑 IPC + 订阅。

## 5. 安全注意

- token 不要写 URL query，避免进历史/日志；
- token 不要写 localStorage；
- 渲染层日志不要打印完整 token；
- `additionalArguments` 仍在进程启动参数里，本机进程可见，但比持久化存储风险低；
- 后端只绑定 `127.0.0.1`。

## 6. 排查清单

```text
baseUrl 仍是 8000
  → 窗口是否在 startServices 之前创建？
  → additionalArguments 是否拼错？
  → preload 是否在 webPreferences 里？
  → readArg 的 prefix 是否与注入名一致？

token 为空
  → startServices 是否成功？
  → 是否被默认值覆盖？
  → 后端是否在无 token 模式启动？
```

## 7. 延伸阅读

- [03-主进程传参additionalArguments.md](03-主进程传参additionalArguments.md)
- [02-Electron后端子进程编排.md](02-Electron后端子进程编排.md)
- [24-桌面端分层与模块封装.md](24-桌面端分层与模块封装.md)

## 扩展阅读

### 站内（本仓）

- [03-主进程传参additionalArguments](03-主进程传参additionalArguments.md)
- [02-Electron后端子进程编排](02-Electron后端子进程编排.md)
- [31-踩坑-桌面端拉起后端的进程环境](31-踩坑-桌面端拉起后端的进程环境.md)

### 站外知识

- [Electron · 上下文隔离](https://www.electronjs.org/docs/latest/tutorial/context-isolation)
- [Electron · 进程模型](https://www.electronjs.org/docs/latest/tutorial/process-model)
