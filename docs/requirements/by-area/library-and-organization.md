# 资源库与组织 · 跨类型需求

> 适用于所有 Resource 类型。具体类型差异见 `by-type/`。

## 1. 领域模型

- `Resource`：用户感知的作品/图片/视频/目录；不是物理文件。
- `ResourceFile`：primary / page / cover / thumbnail / subtitle / episode / extra / launch。
- `Category`：按资源类型独立的分类树，最多 4 层，多对多 `resource_categories`。
- `Tag`：跨类型扁平标签。
- `Collection`：手动合集，成员可跨类型，可排序。
- `SavedView`：保存的时间线筛选规则（无成员表）。
- `ResourceStatus`：active / trashed / lost。

## 2. 已实现

- 导入：文件/目录、复制入库、sha256 去重、缩略图、EXIF/ffprobe。
- 分类树：每类型独立、父子层级、计数含后代、`待整理分类`、删除保护。
- 标签、合集、批量打标/分类、合集导出。
- 资源库 `/library/:type`：类型 tabs、分类树、网格/Justified、筛选、批量。
- 全局搜索、排序、回收站、恢复/彻底删除。
- 首页 `/library/home`：最近添加、合集、时间线、概览。
- 数据失效统一走 `library.invalidate`，避免手动刷新。
- 时间线中心 `/timelines`、日期/时间线备注、GPS 地图。

## 3. 部分实现 / 缺口

| 能力 | 状态 | 说明 |
|------|------|------|
| 批量加入多个合集 | 未实现 | 当前单合集；R1 开放项 |
| 批量移出合集 | 未实现 | 合集详情可单项移出；批量入口未做 |
| 智能合集 | 未实现 | 只有手动合集 |
| 分类多节点并集筛选 | 部分 | 当前单节点含后代；多节点并集在模型里支持，UI 未完全开放 |
| 时间线详情网格视图 | 未实现 | 当前只有竖向 Justified + 地图 |
| 旧库缩略图回填 | 部分 | 新导入有缩略图；旧资源可能读原图 |
| 回收站内预览 | 部分 | 列表可用，查看器验收未收口 |

## 4. 明确边界

- 不把“分类”做成标签；分类有树、类型、删除保护。
- 不把“时间线”做成成员表；规则实时匹配。
- 不把合集成员从主库物理移走；只建立关系。
- 不引入在线图床/分享/多用户。

## 5. 入口

- `apps/backend/app/library/application/use_cases.py`
- `apps/backend/app/library/infrastructure/repositories.py`
- `apps/desktop/src/renderer/src/views/LibraryWorkspace`
- `apps/desktop/src/renderer/src/views/Collections`
- `features/library-workspace/`、`features/library-collections/`、`features/batch-tag-export/`
