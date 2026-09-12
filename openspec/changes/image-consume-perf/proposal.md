# 提案 · image-consume-perf

> 与 `docs/requirements/features/image-consume-perf/需求.md` 同范围。

## Why

浏览和看图被原图解码、词表请求、详情反复拉取、后端多次 hydrate、查看器每帧重算拖慢。

## What Changes

1. **懒加载**：屏外卡片不解码；`/content` 仅查看器打开后。  
2. **面板图**：信息栏与编辑弹窗只用 `thumbnailPath`。  
3. **词表不阻塞**：分类/标签不 `await` 进列表首屏，不挡住信息栏字段。  
4. **缓存**：详情与词表内存缓存；静态文件 Cache-Control。  
5. **后端**：详情一次加载关联；文件响应缓存头。  
6. **前端**：查看器 rAF/resize 防抖；点选少整表重绘。

**BREAKING：** 无 JSON 字段删除。

明确不交付：视频、新 REST 前缀、换 SQLite。

## Capabilities

### Modified Capabilities

- `desktop-image-viewer`：跟手、懒加载原图、面板缩略图  
- `library` 查询/文件流：hydrate 与缓存头（行为不变、更快）

## Impact

- renderer：http 缓存、InfoPanel/Modal、Card、Viewer 封装  
- backend：`repositories._hydrate`、`FileResponse`  
