# 设计 · anime-av-types

> 与 `docs/requirements/features/anime-av-types/实现方案.md` 同一清单。

## 上下文

Resource 当前 = 可网格展示的单媒体。系列需要两级：作品（列表）与集/特典（播放）。参考产品对照见需求 §11：取 Jellyfin 式季集树 + GRM 式作品一卡，不取源路径库与刮削。来源目录异构，库内只保留规范树。文件名映射对齐 Anitopy 元素（标题/季/集/字幕组）。

## 与现有架构对齐

- 作品走 library resources；子树新表，详情在 QueryService 组装  
- 播放不改 overlay 组件，只改 src 为集文件  
- 导入仍 `ImportService` job，内部换 series_ingest（预览→确认）
- 女优独立表；字幕为 files.role=subtitle

## 目标 / 非目标

同实现方案 §2。

## 方案

文件清单见实现方案 §3。

数据流：A-min 见实现方案 §4 浏览播放 + 简化导入（识别则入库，不识别则失败）。A-plus 才强制预览 UI。开发顺序见实现方案 §8。

`VIDEO_LIKE` 仅用于探测/播放器；**列表 type 不得把集当成 video**。

## 决策

同实现方案 §5。

## 风险 / 迁移

同实现方案 §6。0008 重建 CHECK 时拷齐 author、category_id。
