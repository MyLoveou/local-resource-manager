---
name: search-first
description: >-
  加依赖、新工具、新抽象前先搜仓库与现成方案。
  触发词：加包、新依赖、有没有库、能不能用现成的、integrate。
origin: ECC search-first（通用版）
---

# 先搜后写（Search First）

> 禁止在未搜索代码库与文档前重复造轮子。

## 何时触发

- 用户要「加 npm 包」「集成 X」
- Agent 准备新建 util/hook/通用组件
- 新 API 可能已有类似 Controller

## 流程

### 1. 仓库内（必做）

- Grep / SemanticSearch：同类 API、组件、types
- 读 `{API_DESIGN_DOC}` 是否已有端点
- 读 `{API_CLIENT_DIR}` 是否已有 client 方法

### 2. 决策

| 信号 | 动作 |
|------|------|
| 项目内已有 | **扩展**现有代码，最小 diff |
| 文档已定义未实现 | 按契约实现，不新造 path |
| 确需新依赖 | 说明理由；优先轻量、兼容 license |
| 无合适方案 | 自建，记录为何不用现成 |

### 3. 输出

```markdown
## Search First
- 需求：…
- 仓库内命中：… / 无
- 决策：复用 / 扩展 / 新建
- 理由：…
```

然后进入 `project-spec` apply、`plan-workflow` 或按栈实现。
