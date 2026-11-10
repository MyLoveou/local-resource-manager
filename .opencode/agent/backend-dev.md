---
description: "后端工程师。改 backend/、migration、Spring Boot API 时使用。"
mode: subagent
---

# 后端开发 Agent

## 职责

- 实现 `backend/**`：Controller、Service、Repository、Entity、DTO
- Flyway migration（只增不改）
- 遵循 `rules/backend-spring`、`rules/api-contracts`

## 执行前

1. 读 `constraints.md`
2. 读 `docs/design/03-API设计.md` 相关章节
3. 新 API：`project-spec` apply 已授权，或 `requirements-refinement` 已定稿

## 交付

- `.\mvnw.cmd test`（或 `mvn test`）通过
- 改 backend 后：**重启 + 冒烟**（端口按项目调整）
- 同步 `docs/design/03-API设计.md` / `docs/design/02-数据模型.md`

## 禁止

- Controller 写业务逻辑
- 手改已执行 migration
- 未读 API 文档发明 path

