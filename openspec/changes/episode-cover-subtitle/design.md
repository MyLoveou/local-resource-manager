# 设计：每集封面与字幕

完整推导见 `docs/requirements/features/episode-cover-subtitle/实现方案.md`，这里只固定关键决策。

## 决策

| 决策 | 结论 | 理由 |
|---|---|---|
| 字幕与集的关联 | 新表 `subtitle_tracks`，`episode_id` 可空 | 空值即资源级，单文件视频无需第二套表 |
| 字幕文件存哪 | 仍是 `files(role='subtitle')`，关联表只存指针 | 复用现有存储与签名 URL，不复制二进制 |
| 唯一性 | `(file_id, COALESCE(episode_id,0))` 唯一索引 | 防重复挂载，且允许同一字幕挂多集 |
| 匹配策略 | 集号 > 相似度 > 单视频直挂 > 不挂 | "宁缺勿错"：错挂比不挂更难发现 |
| 封面来源 | ffmpeg 抽帧（第 3 秒），失败回退作品封面 | 不引入新依赖；无 ffmpeg 也不能让导入失败 |
| ass/ssa | 入库但 `renderable=false` | 静默失效最糟，必须显式标注 |
| 抽帧时机 | 导入收尾异步 | 不拖慢导入；封面不是导入成功的前提 |

## 分层与文件

```text
library/application/subtitles.py        发现/匹配/语言推断（纯函数 + 少量 IO）
library/application/episode_covers.py   抽帧与登记
library/infrastructure/repositories_subtitles.py   subtitle_tracks 读写
library/infrastructure/media_paths.py     episode_cover_url()
library/api/subtitles.py                 subtitles / episode cover 路由
library/application/series_plan.py       不改
```

## 数据流

```text
导入 → files/episodes 落库 → 扫描字幕 → subtitle_tracks
                              ↘ 异步抽帧 → files(episode_cover) → episodes.cover_file_id
读取 → GET /resources/{id}/episodes(coverUrl,hasSubtitles)
     → GET /resources/{id}/subtitles(episodeId?) → tracks(renderable)
播放 → <video> + <track>（srt 前端转 vtt）
```

## 失败语义

- 字幕发现失败：只记日志，导入照常完成。
- 抽帧失败 / 无 ffmpeg：返回 None，UI 回退作品封面。
- 关联写入冲突：忽略重复（唯一索引 + INSERT OR IGNORE）。
