## Why

列表已经能展示演示数据，但用户无法把本机文件变成库。上一轮「登记根 + 只记账源路径」无法承载后续类型（视频字幕/封面、其它资源包），也让前端可能染上文件 IO。导入必须是：选一次、复制进库、按类型扩展。

## What Changes

- 导入向导：先选资源类型，再选文件或文件夹；系统对话框只返回路径。
- **BREAKING（相对上一轮草案）**：不做持久库根、不做「立即扫描」；选目录只在当次收集来源。
- 后端复制到 `{library_store}/{type}/{id}/` 资源包，写 `resources`/`files`，计算元数据，用 job 报告进度。
- 图片：包内单文件；封面走通用 `resolve_cover`（回退 primary）。视频本轮只复制 primary；字幕/抽帧等专项后续做。
- 资源包布局封装：通用角色 API + 按类型 Layout；导入器不手写库内路径。
- 库目录位置不产品化（设置模块再做）。文件模式允许单选/多选。
- 共享 `FileOps`；类型导入策略可登记；本轮启用 image/video。
- 新库不再 demo seed；旧库演示数据不管。

## Capabilities

### New Capabilities

- `library-ingest`：按类型复制入库、资源包布局、去重、导入任务进度。
- `desktop-import-entry`：分步向导、仅选择路径、进度展示、导入后刷新。

### Modified Capabilities

- （无已归档 main spec。）

## Impact

- 后端：`shared/fs`、`library` importers、imports API、可能 `files.role` 迁移、lifespan seed。
- 桌面：dialog IPC、导入向导、job 轮询。
- 明确不改：scrape/download 业务、回收站语义、token 校验。
