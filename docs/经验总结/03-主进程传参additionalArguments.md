# 03 · 主进程传参：additionalArguments（为什么不用 process.env）

## 结论

**渲染进程拿不到主进程动态算出的值（如后端端口）。`process.env` 跨进程不可靠**——Electron 渲染进程是独立 Chromium 进程，main 里 `process.env.X = ...` 的修改，preload 里不一定读得到。

**正确做法**：`BrowserWindow.webPreferences.additionalArguments` 把值以 `--name=value` 命令行参数传给渲染进程，preload 从 `process.argv` 解析。

## 实现

### 主进程（main/index.ts）

```ts
const win = new BrowserWindow({
  // ...
  webPreferences: {
    preload: join(__dirname, '../preload/index.js'),
    sandbox: false,
    contextIsolation: true,
    additionalArguments: [
      `--backend-url=${backendUrl}`,    // 起完后端才有值
      `--backend-token=${backendToken}`,
    ],
  },
})
```

**时序**：必须先 `await startServices()` 拿到地址，再 `createWindow()`。

### preload（src/preload/index.ts）

```ts
function readArg(name: string): string | undefined {
  const prefix = `--${name}=`
  const arg = process.argv.find((a) => a.startsWith(prefix))
  return arg?.slice(prefix.length)
}

const api = {
  backend: {
    baseUrl: readArg('backend-url') ?? process.env.BACKEND_URL ?? 'http://127.0.0.1:8000',
    token: readArg('backend-token') ?? process.env.BACKEND_TOKEN ?? ''
  }
}
contextBridge.exposeInMainWorld('electron', api)
```

### 渲染进程（infrastructure/http/client.ts）

```ts
const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
const client = axios.create({
  baseURL: window.electron?.backend?.baseUrl ?? DEFAULT_BASE_URL,  // 注入优先，默认兜底
  timeout: 10000,
})
```

## 排查方法（本次实测）

- 渲染进程日志：`[client] backend = {"baseUrl":"http://127.0.0.1:58765","token":"..."}`
- 注入成功后 baseUrl 指向动态端口；若仍指向 8000 → 注入没生效，查 `additionalArguments` 是否在 createWindow 前准备好、preload `readArg` 是否解析到

## 延伸

- **兜底值**必须在（`?? 默认`），否则单浏览器调试（无 preload）时 `window.electron` 为 undefined 会崩。
- 若值很多，可改用 IPC：preload `ipcRenderer.invoke('get-backend')`，主进程 `ipcMain.handle` 返回——但多一次异步，本次用同步 additionalArguments 更简单。

## 扩展阅读

### 站内（本仓）

- [02-Electron后端子进程编排](02-Electron后端子进程编排.md)
- [17-踩坑-process.env跨进程](17-踩坑-process.env跨进程.md)
- [42-图解-一次请求的完整旅程](42-图解-一次请求的完整旅程.md)

### 站外知识

- [Electron · 上下文隔离](https://www.electronjs.org/docs/latest/tutorial/context-isolation)
- [Electron · 进程模型](https://www.electronjs.org/docs/latest/tutorial/process-model)
- [MDN · HTTP 概述](https://developer.mozilla.org/zh-CN/docs/Web/HTTP)



# 问题备注

在这一块，我一直在思考为什么明明没有在任何地方进行显式传递各种参数，比如backend-url这些，它们到底是如何传递的，

我认为是框架在帮忙传递，但实际流程我还不知道
