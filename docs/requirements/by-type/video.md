# 视频（video） · 需求

> 类型配置：`file` 导入、`owned` 存储、内置视频播放器；扩展名 `mp4/mkv/avi/mov/webm/flv/ts/m4v`。
> 视频是“单个视频文件”，不是番剧/AV 的系列作品；系列见 [anime.md](anime.md)、[av.md](av.md)。

## 1. 已实现

- 单文件/文件夹导入、复制入库、sha256 去重、ffprobe 读取时长/分辨率/编码/帧率/码率。
- 内置播放器（双击/再次点击打开）；合集详情、主页、资源库统一走 `openResource`。
- 封面：支持用户选封面、视频抽帧等通用封面能力。
- 分类、标签、合集、批量、回收站、搜索/排序（时长/分辨率/码率）。
- 视频可进入时间线（`creation_time` 优先），未知时间进入未知组。
- 元数据抓取：视频走 TMDB/B站等现有抓取链路（以候选确认结果为准）。

## 2. 部分实现 / 未实现

| 能力 | 状态 | 说明 |
|------|------|------|
| 视频 GPS/地图 | 部分 | 解析 ffprobe `location` / QuickTime ISO6709；有 GPS 且加入地图的视频显示；无 GPS 不显示 |
| 字幕管理 | 部分 | 支持添加外挂字幕；批量/自动匹配未确认 |
| 播放进度记忆 | 未实现 | 当前不持久化播放位置 |
| 视频刮削字段完整度 | 部分 | TMDB/B站字段按现有适配器；站点覆盖有限 |
| 系列化视频 | OUT | 多集作品应使用 anime/av 的系列类型 |

## 3. 候选

- 播放列表/连续播放增强。
- 视频章节、字幕下载、播放进度。
- 视频封面批量重选。
- 与合集导出的更多命名策略。

## 4. 明确不做

- 视频转码/剪辑。
- 下载器内置（下载统一委托第三方，D-20261007-01）。
- 把下载电影默认塞进时间线（无拍摄时间默认不进，可手动计入）。

## 5. 入口

- `apps/backend/app/library/application/media_probe.py`
- `apps/desktop/src/renderer/src/components/VideoPlayerOverlay`
- `features/metadata-scrape/`、`features/library-covers-complete/`
