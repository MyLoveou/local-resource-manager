# 设计 · library-trash

> 与 `docs/requirements/features/library-trash/实现方案.md` 同一套分层与文件清单。

## Context

见 proposal Why。现状：`Resource.to_trash()` / `restore()` 已有；`DELETE /{id}` 软删；列表已支持 `status` 且 `type` 可空；无 restore/purge/batch API；无 `/trash`；`selection` 仅 `selectedId`；`library.bump(type)` 只刷新匹配类型页，回收站与删除后列表不同步是已知债。

基线：软删默认；渲染只 HTTP；入库/删盘只在后端；路径只在 ResourcePackage 内拼。

## Goals / Non-Goals

**Goals：** 沿用 library 分层补 restore/purge/batch；桌面多选 + 回收站页；mutation 后 bump 让所有相关列表 reset。

**Non-Goals：** 新表、新进程、右键菜单、渲染进程删盘、改 DELETE 语义。

## Decisions

| 决策 | 选择 | 不选 |
|------|------|------|
| 彻底删除 HTTP | `POST /{id}/purge` | 再用 DELETE（已占软删） |
| 批量 | 一个 `POST /batch` + `action` | 三个批量路径 |
| 部分失败 | 逐条独立提交 | 整批事务回滚（与契约冲突） |
| purge 顺序 | 先 `remove_tree` 成功或包已不存在，再 DROP | 先 DROP 后删盘（孤儿包） |
| 多选 | 先点「批量删除/选择」进模式，单击切换；沿用 selection store | 浏览时 Ctrl/Shift 随时多选 |
| 回收站数据 | 现有 list `status=trashed`、type 空 | 新 overview 接口 |
| 清空 | 前端分页拉 id 再分批 batch purge | 本轮不加 purge_all（可后置） |
| 列表同步 | bump 无 type 时所有 `useResourcePage` reset；成功后也可本地滤 id | 只 bump(importedType) |

## Risks / Trade-offs

- 清空大回收站多次 round-trip → 上限 200/批，可接受。
- purge 包占用中无法删 → 返回错误、行保留。

## Migration Plan

无新迁移。先后端 API + 单测，再前端路由与多选。回滚代码即可；已 purge 不可回滚。

## Open Questions

无设计级未决（产品假设见需求 §6–7）。
