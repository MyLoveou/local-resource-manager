# 领域层（渲染进程）

与后端共享的**类型定义与领域接口**（跨服务契约的影子）。集中管理全部类型，避免散落。

- 实体类型：Resource / Metadata / Tag / DownloadTask…
- 仓库接口：ResourceRepository、MetadataRepository…
- 通用枚举与常量（资源类型、任务状态）
