# 跨会话续作 · section-visibility

> 换会话先读本文再动手。结束未完成的会话必须更新。

## 状态

- change：`section-visibility`
- 阶段：`待验收`
- 最后更新：2026-10-07 · 实现完成，静态门禁与后端回归全绿；Electron 手验未跑

## 已完成

- tasks：1.1–1.3、2.1–2.2、3.1–3.5、4.1–4.2、5.3
- 代码：`domain/visibility.ts`（新）、`domain/menu.ts`、`App.vue`、`domain/mediaTypes.ts`、`router/index.ts`、`views/Home/index.vue`
- 测试：R1 PASS / R2 PASS；T1–T5 未跑（需 Electron）

## 下一步（新会话按此执行）

1. Electron 手验 T1–T5（菜单/路由/导入/首页/空配置/子路径）
2. 通过后勾选 tasks 5.1–5.2，跑 verification-gate
3. 用户要求时再 archive

## 阻塞

- 待你确认：Electron 手验结果
- 技术阻塞：无

## 关键路径

- 规划：`openspec/changes/section-visibility/`
- 规范：`docs/requirements/features/section-visibility/需求.md`
- 设计：`docs/requirements/features/section-visibility/设计.md`
- 架构：`docs/requirements/features/section-visibility/实现方案.md`
- 代码：
  - `apps/desktop/src/renderer/src/domain/visibility.ts`
  - `apps/desktop/src/renderer/src/domain/menu.ts`
  - `apps/desktop/src/renderer/src/App.vue`
  - `apps/desktop/src/renderer/src/domain/mediaTypes.ts`
  - `apps/desktop/src/renderer/src/router/index.ts`
  - `apps/desktop/src/renderer/src/views/Home/index.vue`
- 基线：`openspec/baseline.md`
- 事实：`docs/product/facts.md`
- 决策：`docs/product/decisions.md`

## 命令备忘

```powershell
openspec status --change "section-visibility" --json
pnpm --filter desktop typecheck
pnpm --filter desktop lint
pnpm --filter desktop build
```

## 规范待决断（本 change 产生）

- 无
