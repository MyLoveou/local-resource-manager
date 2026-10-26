# 08 · 踩坑：端口获取永远 reject

## 现象

后端永远起不来；`startBackend` 第一步 `await getFreePort()` 直接抛错。

## 代码（错误版）

```ts
export function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer()
    srv.listen(0, '127.0.0.1', () => {
      const port = (srv.address() as AddressInfo).port
      srv.close(() => reject(port))   // ❌ 手滑写成 reject
    })
    srv.on('error', reject)
  })
}
```

## 根因

`srv.close(cb)` 的回调里应把端口作为**成功结果**回传——`reject(port)` 导致 Promise 以"端口号"作为错误被拒绝。调用方 `startBackend` 第一步就炸，后面全不执行。

## 修复

```ts
srv.close(() => resolve(port))   // ✅
```

## 教训

- 监听/回调边界处最容易手滑 `resolve`/`reject` 互换。
- 这种 bug 症状很"远"（表现为后端没起来、界面连不上），但根因在最底层第一步。**排障从调用链最前端（端口获取）开始**。
- 单元测试能 5 秒抓到：`getFreePort()` 应 resolve 一个端口数字。

## 扩展阅读

- [02-Electron后端子进程编排](02-Electron后端子进程编排.md)
- [09-踩坑-健康检查未就绪崩溃](09-踩坑-健康检查未就绪崩溃.md)
- [48-图解-启动时序与发布流水线](48-图解-启动时序与发布流水线.md)
