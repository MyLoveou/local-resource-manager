---
name: eval-harness
description: >-
  先写可判定的通过/失败标准再实现。触发：验收标准、eval、回归、tests.md、先定义成功再写代码。
origin: 项目规范
---

# 评测清单

> 先定义「怎样算做成」，再写代码。OpenSpec 变更以 change 内 `tests.md` 为功能级清单；本 Skill 管跨功能回归与无 OpenSpec 时的 eval 文件。

## 何时用

- 新功能、大改 API、新 migration
- OpenSpec propose 结束时：把 spec 场景抄进 `tests.md`
- 需要可重复证据、跨会话回归

## 存放

| 场景 | 路径 |
|------|------|
| OpenSpec 变更 | `openspec/changes/<name>/tests.md` |
| 无 OpenSpec / 跨能力回归 | `evals/<feature>.md`（可 git） |

## 能力级

对照 spec 场景，每条有命令或明确手工步骤。禁止只有 happy path。

## 判定方式（优先靠命令）

1. **代码** — 单测、构建
2. **契约** — 文档与实现一致（可 grep）
3. **冒烟** — HTTP / 页面主路径
4. **人工** — 安全与产品高风险（步骤写清）

流程：定义 → 实现 → 实跑 → 记录 → `verification-gate`

## 反模式

- 太慢从不跑
- 用 eval 绕过范围确认
- 臆造 PASS
