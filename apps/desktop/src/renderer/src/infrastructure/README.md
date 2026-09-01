# 基础设施层（渲染进程）

技术细节实现：HTTP 客户端、IPC bridge 封装、本地缓存。

- `http/` — 后端服务 REST 客户端（axios 实例 + 端点函数）
  - `client.ts` — axios 实例（baseURL 由主进程注入，token 鉴权，超时）
  - `overview.ts` — 首页概览端点（/library/overview）
- `ipc/` — 主进程 bridge 封装
- `cache/` — 本地缓存（缩略图等）

依赖方向：infrastructure → 无上层依赖；被 application/hooks 使用
