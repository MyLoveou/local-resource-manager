# 提案 · library-trash

> 与 `docs/requirements/features/library-trash/需求.md` 同范围。

## Why

用户只能从信息栏把一条资源软删进 `trashed`，之后没有回收站页、没有恢复/彻底删除 API、没有多选批量。删除后网格还可能与库不一致。媒体库闭环缺这一段。

## What Changes

- 左侧「回收站」`/trash`：`GET /library/resources?status=trashed` 混排网格。
- 单条：保留 `DELETE` = 软删；新增 restore、purge（删库内包 + DROP 行）。
- 批量：`POST /library/resources/batch`；须点「批量删除」进入选择模式后再移入回收站。
- 清空回收站（确认后分批 purge）。
- 删除/恢复/彻底删后当前网格立刻与库一致。

**BREAKING：** 无。`DELETE /{id}` 仍为软删（D-20260912-01）。

明确不交付：定时清空、lost 重定位、完整右键菜单、删用户源文件、只删库留盘、全局 Notify。

## Capabilities

### New Capabilities

- `library-trash-lifecycle`：软删幂等、恢复、彻底删除（包 + 行）、批量部分失败
- `desktop-trash-browse`：回收站路由、多选、确认框、列表与库同步

### Modified Capabilities

- （无主 spec 增量。`DELETE`=软删已在归档/进行中的 resource API 约定中，本 change 不改该句。）

## Impact

- API：`POST .../restore`、`POST .../purge`、`POST .../batch`
- 表：无新表；purge DROP 行 CASCADE
- 前端：route `/trash`、selection 多选、`useResourcePage` type 可空、InfoPanel 按钮随 status
- 磁盘：只删 `{library}/{type}/{id}/`
- 文档：需求/实现方案、API 设计补段
