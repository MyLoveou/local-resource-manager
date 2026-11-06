# 架构决策记录（ADR）

> 只放**架构级**决策：分层、模块边界、跨模块契约、技术选型的取舍。
> 产品/功能拍板仍写 [`../../product/decisions.md`](../../product/decisions.md)，**不要两边各写一套**。

## 与 decisions.md 的分工

| 问题 | 落点 |
|------|------|
| 产品方向、能力范围、IN/OUT 拍板 | `docs/product/decisions.md`（压缩条目 ≤8 行） |
| 分层/模块边界/跨模块契约的技术取舍 | 本目录 `NNNN-<kebab-name>.md` |
| 单能力的模型/交互/拆分 | `docs/requirements/features/<id>/设计.md`（L2） |

## 命名与登记

- 文件名：`NNNN-<kebab-case>.md`，四位递增，不复用编号。
- 状态词：`提议` / `已接受` / `已取代`（被取代时在文首指向新 ADR）。
- 新 ADR 用 [`0000-template.md`](0000-template.md)。

## 何时必须写

触发 `/project-spec` L3「跨模块或分层有争议 → 委派 @architect」，或改动以下之一：

- 进程/服务拓扑（如 Electron ↔ 后端 ↔ 引擎子进程）
- 分层依赖方向或新增一层
- 跨模块共享契约的归属（谁定义、谁消费）
- 关键技术选型（数据库、引擎、第三方库的替换）

## 索引

| 编号 | 标题 | 状态 |
|------|------|------|
| — | 暂无。既有架构结论目前集中在 `docs/product/decisions.md` 与 `docs/design/02-数据模型.md`；后续新增架构决策从此表登记。 | |
