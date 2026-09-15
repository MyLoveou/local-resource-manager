# 设计 · anime-av-types

> 与 `docs/requirements/features/anime-av-types/实现方案.md` 同一清单。

## 上下文

Resource 当前 = 可网格展示的单媒体。系列需要两级：作品（列表）与集/特典（播放）。Jellyfin Shows：Season 文件夹 + Season 00/Specials + extras。

## 与现有架构对齐

- 作品走 library resources；子树新表，详情在 QueryService 组装  
- 播放不改 overlay 组件，只改 src 为集文件  
- 导入仍 `ImportService` job，内部换 series_ingest  

## 目标 / 非目标

同实现方案 §2。

## 方案

文件清单见实现方案 §3。

数据流见实现方案 §4。

`VIDEO_LIKE` 仅用于探测/播放器；**列表 type 不得把集当成 video**。

## 决策

同实现方案 §5。

## 风险 / 迁移

同实现方案 §6。0008 重建 CHECK 时拷齐 author、category_id。
