---
name: dynamic-workflow-mode
description: >-
  跨会话续作与任务级循环。触发：handoff、上次做到哪、换会话继续、跨前后端多步。
origin: 项目规范
---

# 跨会话与任务循环

有 OpenSpec change 时，**任务进度以该 change 的 `handoff.md` 为准**。  
**项目实现与方向**以 `docs/product/facts.md` 为准；**历次拍板**以 `docs/product/decisions.md` 为准。三套不要混成一份。

## 何时用

- 功能跨多个会话
- 用户说「留 handoff」「下次接着做」
- 需要实现 → 构建 → 冒烟 → 再修 的短循环

## 有 OpenSpec

1. 读 `openspec/changes/<name>/handoff.md`
2. 按「下一步」执行，结束时更新状态、已完成、阻塞
3. 测试结果写回 `tests.md` 记录表

## 无 OpenSpec

才使用 `evals/<feature>-handoff.md`，字段仍为：目标/不交付、输入、输出、eval、下一步。

## 结束会话前

- [ ] 读过并按需更新 `facts.md`（实现或方向变了）
- [ ] 本轮拍板已压缩进 `decisions.md`（无则跳过）
- [ ] handoff 已更新
- [ ] 有【规范待决断】则交给 `knowledge-extract` 列给用户
- [ ] 未勾完的任务保持未勾，不要假装完成
