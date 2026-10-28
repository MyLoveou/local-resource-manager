# 任务：每集封面与字幕

## 1 数据层

- [x] 1.1 迁移 `0033_episode_cover_subtitles.sql`：`episodes.cover_file_id` + `subtitle_tracks` + 索引
- [x] 1.2 旧库上重复执行无副作用；`schema_version` 记为 33

## 2 后端 · 字幕

- [x] 2.1 `application/subtitles.py`：发现（含 Subs/字幕 子目录）、集号优先匹配、相似度兜底、语言推断
- [x] 2.2 `infrastructure/repositories_subtitles.py`：批量挂载、按集/资源查询、解除关联
- [x] 2.3 导入接入：`_ingest_series` / `_ingest_one` 落库后登记字幕，失败只记日志
- [x] 2.4 `api/subtitles.py`：列表（含 `renderable` 与签名 URL）、新增、删除
- [x] 2.5 集列表接口补 `coverUrl` / `hasSubtitles`

## 3 后端 · 每集封面

- [x] 3.1 `application/episode_covers.py`：ffmpeg 抽帧（第 3 秒，320 宽），登记 `files(role='episode_cover')`
- [x] 3.2 无 ffmpeg / 抽帧失败：返回 None，不抛错、不影响导入
- [ ] 3.3 手动换封面接口（`PUT /library/episodes/{id}`）
- [x] 3.4 导入收尾异步生成，同一资源内串行、资源之间不阻塞

## 4 前端

- [x] 4.1 `InfoPanel` 拆出 `EpisodeList.vue`（先拆再改，避免超基线 1314）
- [x] 4.2 选集卡片：封面、集号、标题、字幕角标
- [x] 4.3 `VideoPlayer` 字幕轨：拉取 tracks、`<track>`、srt→vtt 前端转换、关闭/切换
- [x] 4.4 非 renderable（ass/ssa）字幕：禁用并说明「暂不支持渲染」
- [x] 4.5 单文件视频复用同一套字幕入口
- [ ] 4.6 手动「换封面 / 加字幕」入口（信息栏 + 播放器一致）

## 5 验证

- [x] 5.1 单测：发现与匹配、语言推断、封面失败回退、删除级联
- [x] 5.2 接口：列表字段、新增/删除、重复挂载幂等
- [ ] 5.3 手工 A1–A10（见 `tests.md`）
