# 任务 · metadata-panel

> 每项必须是 `- [ ] X.Y …`。开放问题关闭且用户授权 apply 后再勾选实现。

## 1. 对齐

- [x] 1.1 已读基线、`需求.md`、`实现方案.md` 与本 change 的 proposal/specs/design/tests
- [x] 1.2 开放问题已关闭或降级为「确认不影响范围」
- [x] 1.3 实现不超出 `实现方案.md` 的文件清单与分层

## 2. 测试先行（能写先写）

- [x] 2.1 按 `tests.md` 补齐失败用例（GET 404、PATCH 建标签/分类、POST cover 400）
- [x] 2.2 标明每条 spec 场景的测试 ID（T1–T12）

## 3. 实现

- [x] 3.1 后端：0003 categories + ORM + GET 详情/词表 + PATCH + POST cover；`python -m unittest tests.test_metadata_panel -v`
- [x] 3.2 前端：InfoPanel 草稿+保存、弹窗含封面、确认删除、网格同步；`pnpm --filter desktop typecheck`
- [x] 3.3 关键意图已按 comments 规则加注释（tagNames 替换、分类≠type）

## 4. 契约与文档

- [x] 4.1 定稿后同步 `docs/design/02-数据模型.md`（categories + category_id）
- [x] 4.2 `handoff.md` 更新为实现中/待验收

## 5. 验收

- [x] 5.1 自动项 T1–T6 PASS；手工 T7–T12 / R1 待 Electron
- [ ] 5.2 图片页与视频页各走一遍展示/内联/弹窗/换封面/删除
- [ ] 5.3 改 backend 则重启 Electron 后健康检查 200
