# 音频（audio） · 需求

> 类型配置：`file` 导入、`owned` 存储、内置音频播放器；扩展名 `mp3/flac/wav/aac/ogg/m4a/wma/opus`。
> 当前是“音频文件库”，不是音乐流媒体/歌词平台。

## 1. 已实现

- 单文件/文件夹导入，复制入库、sha256 去重。
- 内置播放器（Howler），合集/主页/详情统一 `openResource`。
- 内嵌封面提取（`audio-embedded-cover`）；用户封面可改。
- ffprobe 读取时长等字段；按 duration 排序。
- 分类、标签、合集、批量、回收站、搜索。

## 2. 未实现 / 待确认

| 能力 | 状态 | 说明 |
|------|------|------|
| 播放列表/队列 | 部分 | 当前有按列表打开播放；跨页面队列未设计 |
| 播放进度记忆 | 未实现 | 不持久化播放位置 |
| 歌词/字幕 | 未实现 | 无 LRC/内嵌歌词解析 |
| 专辑/艺术家结构化 | 未实现 | 当前用标签/分类/作者字段过渡 |
| 音频时间线 | 未实现 | 时间线当前只覆盖图片/视频拍摄时间 |
| 音频元数据刮削 | 未实现 | 无 MusicBrainz 等适配器 |

## 3. 候选

- 专辑/艺术家实体与专辑页。
- LRC 歌词、内嵌歌词、播放进度。
- 音频播放队列与随机/循环。
- 音频封面批量提取/替换。

## 4. 明确不做

- 在线音乐服务、版权曲库、社交分享。
- 音频转码/剪辑。
- 把音频强行塞进照片/视频时间线（除非后续有明确的拍摄/发行时间模型）。

## 5. 入口

- `features/audio-embedded-cover/`
- `apps/desktop/src/renderer/src/components/AudioPlayerOverlay`
- `apps/backend/app/library/application/media_probe.py`
