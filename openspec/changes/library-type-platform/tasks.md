# 任务 · library-type-platform

> 用户已授权 apply。分支 `feat/library-type-platform`。

## 1. 对齐

- [x] 1.1 已读 facts、D-20260917-01/02/03、实现方案
- [x] 1.2 按已拍板范围（含游戏 indexed、漫画无阅读器、TypeBrowse）
- [x] 1.3 独立 feat 分支

## 2. 测试先行

- [x] 2.1 T2 未登记 type → 422
- [x] 2.2 T3/T5 音频导入与去重
- [x] 2.3 T4 游戏 indexed；T4b 彻底删除不删源；T11 漫画一条
- [x] 2.4 T6 空列表

## 3. 领域与契约

- [x] 3.1 type_profile + ResourceType + 0009 CHECK + storage_kind
- [x] 3.2 libraryTypes.ts；route 由档案生成；TypeBrowse；删除 views 克隆
- [x] 3.3 Player 按 consumeKind；02-数据模型同步

## 4. 导入与消费

- [x] 4.1 file：audio/novel/model
- [x] 4.2 package：comic owned；game indexed 默认 + owned 可选；trash 看 storage_kind
- [x] 4.3 Howler；model-viewer；shell-open（含绝对路径）；不改 ImageViewer 翻页
- [x] 4.4 CSP；中文注释

## 5. 验收

- [x] 5.1 tests.md 自动项
- [ ] 5.2 T7–T12 手工（须重启 Electron 以跑 0009）
- [x] 5.3 回归自动测；改 backend 后需重启 Electron
