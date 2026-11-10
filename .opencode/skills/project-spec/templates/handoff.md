# 跨会话续作 · `<change-name>`

> 换会话先读本文再动手。结束未完成的会话必须更新。

## 状态

- change：`<name>`
- 阶段：`规划待确认` / `实现中` / `待验收` / `可归档` / `已归档`
- 最后更新：{日期时间} · 会话摘要一句话

## 已完成

- tasks：1.1、1.2
- 测试：T1 PASS / T2 未跑

## 下一步（新会话按此执行）

1.
2.

## 阻塞

- 待你确认：
- 技术阻塞：

## 关键路径

- 规划：`openspec/changes/<name>/`
- 规范：`docs/requirements/features/<id>/需求.md`
- 设计：`docs/requirements/features/<id>/设计.md`
- 架构：`docs/requirements/features/<id>/实现方案.md`
- 代码：
- 基线：`openspec/baseline.md`
- 事实：`docs/product/facts.md`
- 决策：`docs/product/decisions.md`

## 命令备忘

```powershell
openspec status --change "<name>" --json
```

## 规范待决断（本 change 产生）

- （无则写无；确认后交给 `knowledge-extract` 落盘）
