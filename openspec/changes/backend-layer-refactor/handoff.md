# 跨会话续作 · backend-layer-refactor

## 状态

- change：`backend-layer-refactor`
- 阶段：Phase 0–5 已实施并分阶段提交
- 最后更新：2026-10-01

## 已完成

- 基线：resources.md5 → sha256 + 0015 迁移
- Phase 1 内核/utils 收敛
- Phase 2 领域/枚举归位
- Phase 3 ORM 拆分
- Phase 4 settings 补全
- Phase 5 文档

## 未做（另立）

- 跨模块 application 深 import 治理（download/scrape/settings → library.application 收敛）。
- shared/ 是否改名 core/（需另评估 136 处 import churn）。

## 阻塞

- 无。
