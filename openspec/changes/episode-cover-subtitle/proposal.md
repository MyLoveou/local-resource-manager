# 提案：每集封面与字幕

## 为什么

番剧/视频能播了，但选集只有文字、字幕放不出来。两处断裂都在数据模型层：`episodes` 没有封面列，字幕文件与集没有关联，播放器也没有字幕轨。

## 做什么

1. 迁移 `0033`：`episodes.cover_file_id` + `subtitle_tracks` 表。
2. 导入期自动发现并匹配字幕（集号优先、相似度兜底、宁缺勿错）。
3. 导入期异步抽帧生成每集封面，无 ffmpeg 时回退作品封面。
4. 播放器支持字幕选择（srt/vtt 可渲染；ass/ssa 标注不支持）。
5. 信息栏拆出选集列表组件，显示封面与字幕角标。

## 不做什么

- ass/ssa 原生渲染、内嵌字幕轨提取、字幕在线下载、字幕编辑。
- 系列独立详情页（另立 EPIC）。

## 影响面

`apps/backend/app/library/`（application / infrastructure / api）、`apps/desktop/src/renderer/src/components/VideoPlayer`、`ui/layouts/InfoPanel`、`infrastructure/http`。
