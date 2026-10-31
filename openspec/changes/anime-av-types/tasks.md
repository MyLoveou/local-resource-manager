# 任务 · anime-av-types

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

> 第一刀 A-min。须用户说「可以按此实现」后再 apply。第二刀任务先列着，第一刀验收前不要勾做。

## 0. 对齐

- [x] 0.1 已读 facts、D-20260917-01、需求两刀、实现方案 §8
- [x] 0.2 在 `feat/anime-av-types` 做，不把半成品合 master

## 1. 第一刀 · 解堵

- [x] 1.1 `ResourceType`：`anime` / `av`（去掉 `anime-series`）；CHECK 迁移
- [x] 1.2 前端 union、路由 `/anime` 标题「番剧」、向导类型
- [x] 1.3 ResourceBrowser：系列 type 单击不走 `Player[type]`；unmount close 仅 image/video

## 2. 第一刀 · 测试先行

- [x] 2.1 T1/T2 空列表与旧 video
- [x] 2.2 T3 详情含集树
- [x] 2.3 T4 目录导入一作品

## 3. 第一刀 · 进库与播

- [x] 3.1 seasons/episodes（及可选 extras）+ 详情组装
- [x] 3.2 series_ingest：Season 目录 / 序号扁平；import 按 type 分支；probe
- [x] 3.3 InfoPanel 序号集列表 + 点集 overlay
- [x] 3.4 软删作品；中文注释：作品才是 Resource

## 4. 第一刀 · 文档与验收

- [x] 4.1 `02-数据模型.md` 最小 ER
- [x] 4.2 tests.md T1–T6、T8–T9、R1；T7 若 extras 已做
- [ ] 4.3 改 backend 后重启 Electron

## 5. 第二刀 · A-plus（第一刀验收后再做）

- [ ] 5.1 预览改映射；unknown 不自动建集
- [ ] 5.2 删集/追加/canonical rename
- [ ] 5.3 字幕组、字幕轨、女优、集封面双列表、特典完善
- [ ] 5.4 T10–T13
