# 任务 · grid-media-performance

> 用户授权 apply 后再实现。

## 1. 对齐

- [x] 1.1 已读基线、`需求.md`、`实现方案.md` 与本 change 的 proposal/specs/design/tests
- [x] 1.2 开放问题已关闭
- [x] 1.3 实现不超出实现方案文件清单

## 2. 测试先行

- [x] 2.1 RED：`tests/test_grid_thumbnails.py` 覆盖 T1–T5
- [x] 2.2 标明 T6–T8 为桌面构建/手工或可测的节流单测

## 3. 实现

- [x] 3.1 常量 + `ResourcePackage.put_thumbnail` + `thumbnails.py`（Pillow）；验证 T1 路径
- [x] 3.2 `import_service` 在 probe 后生成；失败不挡；无封面视频不写；验证 T2 T3
- [x] 3.3 仓储/schema 映射 `thumbnailPath`；`replace_cover` 覆盖；验证 T4 T5
- [x] 3.4 前端 `thumbnailPath` + ResourceBrowser；VirtualGrid 宽度节流；`pnpm --filter desktop typecheck`

## 4. 契约与文档

- [x] 4.1 同步 `docs/design/02-数据模型.md` 的 role / thumbnailPath
- [x] 4.2 `handoff.md` 改为实现中/待验收

## 5. 验收

- [x] 5.1 跑 `tests.md` 命令，禁止臆造 PASS（T1–T5 + R1 已绿）
- [ ] 5.2 手工：导入图看网格小图、信息栏原图；拖窗口不每像素卡死
