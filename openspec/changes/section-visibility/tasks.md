# 任务 · section-visibility

> 每项写明如何验证。官方 apply 靠 checkbox 追踪。

## 1. 对齐

- [x] 1.1 已读基线、`需求.md`、`设计.md`、`实现方案.md` 与本 change 的 proposal/specs/design/tests
- [x] 1.2 开放问题已关闭（四项范围已确认，无遗留）
- [x] 1.3 实现不超出 `实现方案.md` 的文件清单与分层

## 2. 测试先行（能写先写）

- [x] 2.1 无前端测试框架；以 typecheck/lint/build + Electron 手验作为 `tests.md` 证据（项目无 test script）
- [x] 2.2 每条 spec 场景已映射测试 ID（T1–T5）

## 3. 实现

- [x] 3.1 算法：`domain/visibility.ts` — `HIDDEN_SECTIONS` + `isSectionHidden`（`/` false、未知 path false、子路径前缀命中）；验证：typecheck
- [x] 3.2 功能：`router/index.ts` 守卫命中隐藏 → `/`；验证：手验 `#/av` 与 `#/collections/1`
- [x] 3.3 UI：`domain/menu.ts` 谓词注入 + `App.vue` 组合；`domain/mediaTypes.ts` 导入过滤；`views/Home/index.vue` 卡片过滤；验证：手验三处入口
- [x] 3.4 组合根：四入口同用一份配置，主路径验收（默认清单 5 项）
- [x] 3.5 关键意图中文注释（可见性配置规则、谓词默认行为）

## 4. 契约与文档

- [x] 4.1 无 API/数据模型变更；`facts.md` / `decisions.md` 同步
- [x] 4.2 两处 `handoff.md` 更新为「待验收」

## 5. 验收

- [ ] 5.1 `tests.md` 全部 PASS（贴命令与结果）
- [ ] 5.2 `verification-gate` 输出可交付
- [x] 5.3 未改 backend；跑全量 pytest 回归防误伤
