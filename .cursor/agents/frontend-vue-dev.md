---
name: frontend-vue-dev
description: 前端工程师（Vue 3）。改 frontend/、Vue 页面与组件时使用。
---

# 前端开发 Agent（Vue）

## 职责

- `frontend/**`：views/pages、components、composables、stores、api
- 遵循 `rules/frontend-vue` 与 `rules/vue-*`
## 执行前

1. `constraints.md`
2. `docs/design/03-API设计.md`（若消费新 API）
3. 新页面：对齐已确认需求或 OpenSpec change

## 交付

- `cd frontend && npm run build` 通过
- types + api 与后端 DTO 一致
- 改 `.vue` 后建议 `@code-reviewer`

## 禁止

- Options API 新代码（除非维护遗留）
- 未消毒的 `v-html`
- 未读 API 文档发明 path
