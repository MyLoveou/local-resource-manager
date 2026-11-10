# 工作流触发（自动）

收到用户消息、准备改代码、声称完成前：对照下表，**先读**本平台目录 `skills/<name>/SKILL.md`。

## 快速入口

| 场景 | 入口 |
|------|------|
| 新能力 / 先出方案 | `project-spec`（propose；复杂需求先 L2 设计 STOP） |
| 复杂需求：模型/交互/模块/拆分/UI与算法组合 | `project-spec` 设计阶段（`设计.md` + 切片契约，不是 `project-spec-design`） |
| 按 spec 实现 | `project-spec`（apply；复杂须 L2 已确认） |
| 修 bug / 缺陷 / 复现 | `project-spec-fix` |
| 改样式 / CSS / 对齐 / 间距 | `project-spec-style` |
| UI 设计 / 视觉方向 / 先设计这一页观感 | `project-spec-design` |
| 换会话继续上次 | `project-spec`（先读 facts + decisions，再 handoff） |
| 记住 / 提炼规则 / 反复强调 | `knowledge-extract` |
| 记下这次决策 / 项目方向 | `docs/product/decisions.md` + 必要时改 `facts.md` |
| 提需求、先写中文需求稿 | `requirements-refinement` |
| 只要实现计划、先别写代码 | `plan-workflow`（无 OpenSpec 仓时） |
| 加依赖 / 查现有实现 | `search-first` |
| 代码图 / 调用链 / 影响面 | CodeGraph MCP（见 `mcp/codegraph.md`）；未接入则 Grep |
| 画 mermaid / 时序图 / 流程图 / 状态图 | `mermaid-diagrams` |
| 远程主机 / SSH / 上服务器 | SSH MCP（仅 `hosts.json` 已登记机） |
| 构建失败 | `build-fix` |
| 改 backend 后验收 | `backend-verify` |
| 交付 / 声称完成 / PR | `code-review-gate` → `verification-gate` |
| 跨会话续作 | `facts.md` + `decisions.md`；任务用 `project-spec` handoff；复杂循环可叠加 `dynamic-workflow-mode` |
| 剧本总览 | `workflows/` |

## 界面工艺

先定观感仍是 `project-spec-design`，只改样式的门禁仍是 `project-spec-style`。命中下面的场景先读对应 Skill：

| 场景 | 入口 |
|------|------|
| 快速收拾、防俗套 | `baseline-ui` |
| 键盘、可访问名称、焦点、对比度 | `fixing-accessibility` |
| 动效卡顿、滚动动画、模糊 | `fixing-motion-performance` |
| 按本产品证据审计界面，只出计划 | `improve-ui` |
| 圆角、阴影、图标、微交互 | `better-ui` |
| 分组、对齐、响应式结构 | `better-layout` |
| 字号、行高、换行、截断 | `better-typography` |
| 查看已有组件的变体 | `component-canvas` |
| 并排比较、再试一版 | `create-canvas` |
| 新界面定方向、几种风格要真的不一样 | `oil-ui`（确认前仍停在 `project-spec-design`） |

## 新能力串联

`project-spec`：L1 →（复杂）L2 设计确认 → L3 → apply（含 tests.md）→ `code-review-gate` → `verification-gate`

无 OpenSpec 的仓：`requirements-refinement` 定稿 → `plan-workflow` 用户确认 → 再编码。

