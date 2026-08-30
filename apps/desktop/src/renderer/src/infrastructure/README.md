# 基础设施层（渲染进程）

技术细节实现：HTTP API client、SSE/WebSocket 订阅、IPC bridge 封装。

- `http/` — 后端服务 REST 客户端（抓取服务、下载服务）
- `ipc/` — 主进程 bridge 封装
- `cache/` — 本地缓存（缩略图等）

依赖方向：infrastructure → 无上层依赖；被 application 使用
