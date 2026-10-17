# 提案 · section-visibility

> 对照：`docs/requirements/features/section-visibility/需求.md`（已定稿，同范围）

## 为什么

- 问题：左侧菜单固定暴露全部 13 个分区；部分分区能力未实现或未完整实现（AV 刮削/第二刀、小说/漫画内置阅读器、游戏仅登记、模型仅 gltf/glb 预览），占位菜单造成误导
- 为何现在做：A-min 已可用，进入收口期；需要靠代码配置压低「未完成能力」的暴露面
- 不做的后果：每次演示/自用都要手动忽略尚未完成的分区

## 做什么

- 新增代码级配置 `HIDDEN_SECTIONS`（TS 常量），默认隐藏 `/av` `/novel` `/comic` `/game` `/model`
- 隐藏项在菜单、路由直达、导入向导、首页概览卡四处一致生效
- 隐藏只影响入口；资源、合集、API、数据均不变，清空配置即恢复
- **BREAKING**：无
- 明确不交付：设置页开关、环境变量、按用户/环境切换、搜索/合集过滤、单功能级开关

## 范围

| | 内容 |
|--|------|
| IN | 代码配置；菜单过滤；路由重定向；导入选项过滤；首页卡过滤 |
| OUT | 后端/DB 变更；搜索与合集混排过滤；灰显「建设中」；隐藏 `/`；未知 key 报错 |
| 假设 | 无（四项范围已确认） |

## 能力（Capabilities）

### 新增

- `section-visibility`：代码级分区可见性配置，统一控制菜单/路由/导入/首页入口

## 规范对齐

- 基线条目：单机桌面壳；类型可插拔、菜单占位可早出现（facts 方向）→ 遵守，仅收窄入口
- 动工门禁：L1 `需求.md` 已定稿；L2 `设计.md` 已确认
- 与能力文档 / 禁止项冲突：无

## 现状要点（有路径）

- 菜单：`apps/desktop/src/renderer/src/domain/menu.ts` — `menuFromRoutes(routes)` 由 `App.vue` 调用，过滤 `hideMenu`
- 路由：`apps/desktop/src/renderer/src/router/route.ts` — 类型路由由 `TYPE_PROFILES` 生成
- 导入：`apps/desktop/src/renderer/src/domain/mediaTypes.ts` — `ENABLED_IMPORT_TYPES` 现仅在排除 `work_directory`
- 首页：`apps/desktop/src/renderer/src/views/Home/index.vue` — 渲染后端 `stats.byType`
- 可复用：`TYPE_PROFILES.routePath` / `profileFor` / `menuFromRoutes`

## 影响

- API / 表：无
- 前端路由：隐藏项直达重定向 `/`
- 配置：新增代码常量 `domain/visibility.ts`
- 文档：`需求.md`、`设计.md`、`实现方案.md`、`facts.md`、`decisions.md`

## 验收意图（详情在 tests.md）

- 主路径：默认清单 5 项在菜单/路由/导入/首页一致隐藏
- 失败/边界：空配置=现状；未知 key 忽略；隐藏 `/collections` 时子路径一并拦截
- 回归：不得破坏未隐藏分区的导航与导入

## 开放问题

1. 无（已确认）
