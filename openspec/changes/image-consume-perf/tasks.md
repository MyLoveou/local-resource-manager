# 任务 · image-consume-perf

> 状态（2026-10-31 复核）：**代码项已完成**，剩余为人工在 Electron 内验收（见 `docs/requirements/收尾清单.md` 第三节）。
> 复核方式：逐项在代码里定位实现并记录文件与关键行，未改动业务逻辑。

- [x] 1. 懒加载：卡片/面板图；content 仅查看器打开后；±1 预取 idle
  - 证据：`components/Card/index.vue` 的 `<img loading="lazy" decoding="async">`；
    `PhotoTimeline/PhotoRow.vue`、`JustifiedMediaGrid`、`VirtualGrid` 同为 lazy；
    虚拟列表只挂可见格（`@tanstack/vue-virtual`）。
- [x] 2. InfoPanel + EditResourceModal 预览锁定缩略图
  - 证据：`ui/layouts/InfoPanel/index.vue` 的 `coverUrl = resolveCardImageUrl(resource)`；
    `infrastructure/http/mediaUrl.ts` 里 `thumbnailPath || coverPath` 优先，且带 `updatedAt` 缓存戳。
- [x] 3. 列表首屏与信息栏字段不 await 分类/标签
  - 证据：`LibraryWorkspace`/`ResourceBrowser` 内无 `getCategories`/`getTags` 调用；
    列表只等 `listResources`，词表由面板按需拉取。
- [x] 4. getResource / 词表内存缓存，bump 失效
  - 证据：`infrastructure/http/resources.ts` 的 `detailCache`（上限 50）+ `invalidateResourceCache`。
- [x] 5. FileResponse Cache-Control；`_hydrate` 一次加载关联
  - 证据：`library/api/resources.py` 的 `_file_response`（长缓存 86400s / 短缓存 120s）；
    `repositories_resources._hydrate` 用 3 条 select 一次取标签/文件/待办。
- [x] 6. Viewer resize 防抖、拖拽跟手（先 Viewer.js）
  - 证据：`components/ImageViewerHost/index.vue` 用 `requestAnimationFrame` 合并 resize。
- [x] 7. tests.md + typecheck；后端相关单测
  - 证据：2026-10-31 `pnpm --filter desktop typecheck` / `lint` / `build` 均 exit 0；
    后端全量 `pytest -q apps/backend/tests` **434 passed + 2 subtests**。

## 仍需人工验收（自动化覆盖不到）

| 项 | 操作 | 判据 |
|---|---|---|
| 网格首屏 | 导入一批大图后滚动网格 | 只加载可见行，滚动不白屏 |
| 面板预览 | 点选一张 24MP 图 | 面板显示的是缩略图，不卡顿 |
| 查看器 | 全屏查看后拖窗口边缘 | 缩放跟手，无连续重排 |
| 原图时机 | 打开查看器前后看网络 | content 只在查看器打开后请求 |
