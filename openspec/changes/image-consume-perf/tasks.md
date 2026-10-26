# 任务 · image-consume-perf

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

> 用户确认「可以按此实现」后再编码。

- [ ] 1. 懒加载：卡片/面板图；content 仅查看器打开后；±1 预取 idle
- [ ] 2. InfoPanel + EditResourceModal 预览锁定缩略图
- [ ] 3. 列表首屏与信息栏字段不 await 分类/标签
- [ ] 4. getResource / 词表内存缓存，bump 失效
- [ ] 5. FileResponse Cache-Control；`_hydrate` 一次加载关联
- [ ] 6. Viewer resize 防抖、拖拽跟手（先 Viewer.js）
- [ ] 7. tests.md + typecheck；后端相关单测
