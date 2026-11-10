---
name: code-review-gate
description: >-
  改完代码、合并前、用户要求审查时使用。
  触发词：审查、review、看看改动、合并前、code review。
origin: ECC /code-review（通用版）
---

# 代码审查门禁（Code Review Gate）

## 何时触发

- 用户要求「审查」「review」「合并前看看」
- Agent 完成一项功能改动后（**建议**交付前）
- 改动涉及：Security、JWT、权限、分享链
## 流程

### 1. 按改动类型委派

| 改动 | 审查 |
|------|------|
| 任意业务代码 | `@code-reviewer` |
| `{BACKEND_DIR}/**` Java | `@backend-dev` 自检 + `@code-reviewer` |
| `{FRONTEND_DIR}/**` tsx | `@frontend-dev` 自检 + `@code-reviewer` |
| `{FRONTEND_DIR}/**` vue | `@frontend-vue-dev` 自检 + `@code-reviewer` |

### 2. 必查项（项目填写）

- [ ] 符合 `{CAPABILITY_DOC}` / 已确认规划
- [ ] 对照 `docs/standards/代码审查.md` 严重度与裁决
- [ ] 改领域热路径时对照项目 `docs/standards/{DOMAIN_SPEC}.md`（若有）
- [ ] 权限与鉴权正确
- [ ] 无 `{DEPRECATED_API}` 新引用
- [ ] 契约与 `{API_DESIGN_DOC}` 一致
- [ ] 无密钥、本地库文件误提交

### 3. 输出

```markdown
## 审查结果
- BLOCKER：… / 无
- 建议：…
- 是否可进入 verification-gate：是 / 否
```

有 BLOCKER → 先修再 `verification-gate`。

## 与 verification-gate 分工

| code-review-gate | verification-gate |
|------------------|-------------------|
| 质量、安全、架构 | 构建、重启、冒烟、文档 |
