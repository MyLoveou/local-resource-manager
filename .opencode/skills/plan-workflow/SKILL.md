---
name: plan-workflow
description: >-
  规划、计划、蓝图、怎么拆、实现方案、多 PR 步骤。触发：规划、计划、plan、先别写代码。
origin: ECC /plan（通用版）
---

# 规划工作流（Plan）

> **需求已定稿 → 出 L3 技术方案 → 用户确认 → 再写代码**（除非用户明确「直接做」且承担风险）。

## 前置门禁

- `需求.md` 状态为 **已定稿**
- **复杂需求**：同目录 `设计.md` 已定稿（模型/交互/模块/拆分/抽象/原则）；未完成 → **STOP**，回到 `project-spec` 设计阶段
- 或：用户明确「直接做」且已记录文档滞后风险
- 需求未定稿 → **STOP**，回到 `requirements-refinement`

## 产出（硬交付）

须创建或更新 **`docs/requirements/features/<id>/实现方案.md`**（模板见 `templates/docs-implementation-plan.md`），并满足 `docs/standards/版本与动工门禁.md` §2 L3 checklist。

方案必须强调**项目架构**：沿用现有分层与模块、路径级文件清单、数据流；禁止只写空泛原则。有 OpenSpec 时与 change 的 `design.md` 对齐。

方案状态：`草案` → `评审中` → **`已定稿`**（**用户确认后**方可编码 / `project-spec` apply）。

## 何时触发

- 「规划」「计划」「怎么拆」「蓝图」「技术方案」
- 新能力、多文件/多模块联动
- 任务明显 >1 PR 或 >3 步
- 需求已定稿，准备编码前（**必经**）
- **未**说「直接做」「just do it」

## 流程

### 1. 范围与需求（必做）

读已定稿 `需求.md`、复杂则已定稿 `设计.md` → 读 `docs/standards/版本与动工门禁.md` §1 → IN/OUT 与计划对齐。对照基线、设计中的模块与模型，再写文件清单。

### 2. 现状（只读）

- **大需求**：先摸清代码现状（只读检索 + 证据），再写本方案
- 小改：Task explore 可作轻量替代
- 读 `{API_DESIGN_DOC}`、`{DATA_MODEL_DOC}` 相关章节
- 读 UI：`docs/UI/`、`界面规格.md`、Canvas（若有）
- 未「摸底已核实」（若适用）→ **STOP**，勿进入方案定稿

### 3. 方案输出

写入 `docs/requirements/features/<id>/实现方案.md`，并附聊天摘要：

```markdown
## 实现计划 · <功能名>

### 目标 / 不交付
### 架构与文件清单（路径级）
### 组合根（若拆 UI/功能/算法）
### 数据流（主路径 + 错误路径）
### 契约落点（IPC / domain / migration）
### UI（组件、状态、空态/错误态）
### 测试策略
### 风险
### 步骤（纵向或组合切片；最后一步必须接到页面/门面）
1. …
2. …

### 验收映射（需求 § → 验证方式）
### 验证
- eval：`evals/<feature>.md`（可选）
- 交付：`verification-gate`

```

### 4. 确认门禁

**默认等待用户确认**「方案已定稿，可动工」后再编码。确认后：

1. 实现方案文档状态 → **已定稿**
2. 进入 `project-spec` apply（或按栈直接实现）

### 5. 大任务

跨会话 → `dynamic-workflow-mode` + handoff 文件。

明显多 lane（>3 独立步骤）→ 计划中写清文件所有权，避免并行写同一文件。

## 委派

| 需要 | 使用 |
|------|------|
| 架构 | `@architect` / `@planner` |
| 产品边界 | `@product-manager` |

## 反模式

- 需求未定稿就列实现步骤
- 未确认范围就列步骤
- 发明未登记 API path
- 计划含 OUT OF SCOPE 能力
- 只在聊天里给计划、不落 `docs/requirements/features/<id>/实现方案.md`
- 另起一套与现有 `backend/` `frontend/` 分层无关的架构空话
- 用户未确认方案就开始写 migration / Vue 组件
