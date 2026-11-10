# 任务 · metadata-panel-fields

> 状态（2026-10-31 复核）：**代码项已完成**，并在本轮补上「音轨条数」；剩余为人工在 Electron 内验收。
> 复核方式：逐项在代码里定位实现并记录文件与关键行。

- [x] 1 读需求轮次 3
  - 结论：需求六项（描述、立刻待办、作者、格式、图片分辨率、视频时长/清晰度/分辨率/帧率/码率/画质）均在面板落地。
- [x] 2 RED：字幕、待办、档位、probe mock
  - 证据：`tests/test_media_probe.py`、`tests/test_subtitles.py`（后端全量 434 passed）。
- [x] 3 迁移 author/todos/fps/bitrate + Pillow 依赖
  - 证据：`resources.author`、`resource_todos`、`files.fps`/`files.bitrate` 已在 ORM；图片解码走 Pillow（`image_support`）。
- [x] 4 media_probe + import_service
  - 证据：`media_probe.probe_video` 用 ffprobe 读时长/分辨率/帧率/码率/编码，导入写入 `files`。
- [x] 5 字幕 POST + todos API
  - 证据：`library/api/resources.py` 的 `POST /resources/{id}/subtitles`；`library/api/todos.py`。
- [x] 6 InfoPanel 分块
  - 证据：拆出 `InfoPanelAITab.vue`、`InfoPanelFooter.vue`、`InfoPanelRelationTab.vue`、`InfoPanelCollectionsModal.vue`。
- [x] 7 同步数据模型；验收
  - 证据：`domain/resource.ts` 的 `ResourceFile` 含 exifCamera/exifLens/exifIso/exifAperture/exifShutter；
    `2026-10-31` typecheck / lint / build 均 exit 0。

## 本轮新增字段（2026-10-31）

| 字段 | 位置 | 说明 |
|---|---|---|
| 音轨条数 | 信息栏视频分支 | `音轨 2 条`，仅在 >1 条时显示 |

实现：面板 watch `resource.id + primaryFile().id`，调用
`GET /library/resources/{id}/files/{fid}/audio-tracks`；失败或单音轨时不显示，
避免给普通视频增加噪音。

## 仍需人工验收

| 项 | 操作 | 判据 |
|---|---|---|
| 图片字段 | 选一张带 EXIF 的照片 | 拍摄/机身/镜头/ISO/光圈/快门都正确 |
| 视频字段 | 选一集视频 | 分辨率/清晰度/时长/帧率/码率/画质都有值 |
| 音轨字段 | 选一个双音轨文件 | 显示「音轨 2 条」；单音轨不显示 |
| 待办 | 加一条立刻待办 | 列表即时出现，可完成 |
