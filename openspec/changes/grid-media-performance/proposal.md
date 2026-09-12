# 提案 · grid-media-performance

> 与 `docs/requirements/features/grid-media-performance/需求.md` 同范围。

## 为什么

网格把原图当卡片封面，解码和窗口缩放把主线程打满。L1 已要求缩略图懒加载，虚拟滚动已有，派生小图未做。

## 做什么

- 导入 copy/probe 之后生成一档网格 WebP，落在资源包 `thumbs/grid.webp`。
- 列表增加 `thumbnailPath`；网格优先用它。`coverPath` 仍给信息栏原图。
- 换封面覆盖同一缩略图。失败不挡导入。
- 虚拟网格对宽度节流再重算列。

**BREAKING：** 无（只加字段；旧客户端忽略 `thumbnailPath` 仍用封面）。

明确不交付：视频抽帧、旧库回填、全局缩略图缓存盘、信息栏改小图、导入吞吐优化、预览播放。

## 范围

| | 内容 |
|--|------|
| IN | 导入生成；包内路径；列表字段；网格 URL；换封面重生；宽度节流 |
| OUT | ffmpeg 抽帧；全局 cache；改 cover_path 语义；万级硬门槛 |
| 假设 | 最大边 480、WebP、节流 100–200ms、无封面视频不生成 |

## 能力（Capabilities）

### 新增

- `library-ingest-thumbnails`：导入与换封面在包内写入网格缩略图
- `desktop-grid-browse`：列表用缩略图 URL；窗口宽度节流重排

## 规范对齐

- 基线：渲染只 HTTP；入库 IO 只在后端；路径由 ResourcePackage 拼
- 动工门禁：L1 评审中，待「可以按此实现」
- 与禁止项冲突：无

## 现状要点

- `ResourcePackage`：`{store}/{type}/{id}/` + `primary*` / `cover*` / `subtitles/`
- `import_service`：copy → probe；`cover_path` 指 `/content`（原图）
- `ResourceBrowser`：`coverPath` → `<img>`
- `VirtualGrid`：`useElementSize` 宽度直接算 lanes
- 可复用：Pillow、`FileResponse` content、`FILE_ROLE_*`

## 影响

- API：资源 JSON 增加 `thumbnailPath`
- 表：无新表；`files.role=thumbnail`
- 前端：domain + ResourceBrowser + VirtualGrid
- 依赖：已有 Pillow
- 文档：本能力需求/实现方案、数据模型 `files.role`

## 验收意图

- 主路径：导入图片有 `thumbs/grid.webp`，网格不拉原图
- 失败：生成失败资源仍在
- 回归：信息栏封面仍清晰；去重回滚仍删整包

## 开放问题

无。
