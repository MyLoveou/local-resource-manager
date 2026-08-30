# 基础设施层（Electron 主进程）

桌面端技术细节实现。

- `services/` — 后端服务**进程编排**：启动/停止抓取服务与下载服务、端口与 token 管理、健康检查
- `ipc/` — 主进程 IPC handler 注册
- `store/` — 主进程侧持久化（userData 路径、数据库位置）
