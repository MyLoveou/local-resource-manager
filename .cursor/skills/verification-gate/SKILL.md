---
name: verification-gate
description: >-
  交付前验证门禁。触发：验收、DoD、交付、提 PR、完成、tests.md、声称结束。
origin: 项目规范
---

# 验证门禁

> 权威 DoD：project constraints · 本 Skill 正文

## 何时使用

- 功能或显著改动完成后
- 用户要求「验收」「DoD」「交付前检查」
- 创建 PR 前
- 改 backend 或 API 契约后

## 阶段 0：范围与设计

- 读 `facts.md` / 浓缩基线；对照 change 或 `需求.md`，确认未越界
- **复杂需求**：`设计.md` 已定稿；组合式则切片契约已填。否则 **STOP**（G1a），结论=阻塞
- 有 `tests.md`：未跑完不得标可交付

## 阶段 1：前端构建

```powershell
{FRONTEND_BUILD_CMD}
```

失败 → **STOP**。

## 阶段 2：后端构建

```powershell
{BACKEND_BUILD_CMD}
```

可选：`{BACKEND_TEST_CMD}`。失败 → **STOP**。

## 阶段 3：切片测试（若 L2 采用组合式）

- [ ] 算法：单测或可重复脚本 PASS
- [ ] 功能：用例/接口检查 PASS
- [ ] 组合根：主路径在页面（或约定入口）可走通
- 只交了算法或只交了控件 → **不可交付**

未拆切片：跳过本阶段，仍须主路径检查（在 `tests.md`）。

## 阶段 4：后端重启（若改了 backend/**）

1. 停旧进程（端口 `{BACKEND_PORT}`）
2. `{BACKEND_RUN_CMD}`
3. migration 日志无失败
4. HTTP 冒烟改动接口（见 `{DEV_ACCOUNTS_DOC}`）

仅改 frontend/docs → 跳过。

## 阶段 5：契约、注释与文档

- 若改 API/实体：更新 `{API_DESIGN_DOC}`、`{DATA_MODEL_DOC}`
- 改过的代码符合 `comments` 规则
- OpenSpec change：`tests.md` 记录为 PASS，`handoff.md` 已更新
- 复杂需求：`设计.md` / `实现方案.md` 仍与代码同范围
- 经验总结：`temp/经验总结/<项目>/` 新增一条（先搜后写；结论 + 原理 + 可验证实验），见 `skills/learning-notes`

## 阶段 6：仓库卫生

- [ ] 未提交密钥、`.env`、本地库
- [ ] 用户未要求时不 commit/push

## 输出格式

```markdown
验证门禁 · {PROJECT}
- 范围：通过 / 需说明
- L2 设计/切片契约：通过 / 跳过（简单） / 阻塞
- tests.md：通过 / 失败 / 无
- 算法单测：通过 / 跳过 / 失败
- 组合根主路径：通过 / 跳过 / 失败
- frontend build：通过 / 失败
- backend compile/test：通过 / 跳过
- 后端重启+冒烟：通过 / 跳过 / 未执行
- 文档同步：是 / 否 / N/A
- 经验总结：<路径> / 无
- 结论：可交付 / 阻塞：…
```

**禁止臆造通过**。
