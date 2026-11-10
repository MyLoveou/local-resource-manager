---
name: project-spec-style
description: >-
  样式修改特化：只改观感与布局，不改业务契约。触发：改样式、CSS、间距、颜色、对齐、
  不好看、调一下 UI、跟设计稿对齐、hover、响应式。
origin: 项目规范
---

# 项目规范 · 改样式

只动视觉与布局。改交互流程、接口、权限、文案含义 → 转 `project-spec` 或 `project-spec-design`。

## 升级条件

- 新页面/新信息架构
- 改组件 API、路由、接口字段
- 用户要「先定设计方向」而还没有方向 → `project-spec-design`

## 步骤

1. **G0** 读基线。声明 `场景: 改样式`。确认栈：Vue 或 React（本仓可能两者都有，跟文件走）。
2. **钉范围**：页面/组件路径、要改的属性（间距、色、字号、断点）。列出 **不改**：逻辑、接口、文案语义。
3. **跟现有语言**：先搜同页/同设计系统的变量、class、theme；禁止另起一套网上「设计系统」。对照 `baseline-ui`、`better-layout`、`better-typography`、`better-ui`。控件对照 `fixing-accessibility`。已有动效对照 `fixing-motion-performance`。不要为了好看新加动画。
4. 有 `openspec/` 且改动跨多个组件：

```bash
openspec new change "style-<short-name>"
```

`skip_specs: true`。proposal 用 [templates/style.md](../project-spec/templates/style.md)。  
`tests.md`：构建 + 关键态目视清单（默认、hover、空态、窄屏）。

5. 单文件微调且用户要直接改：可无 change，但仍写目视清单并在回复里列出改动文件。
6. 实现最小 diff；遵守 `comments`（只注释非显而易见的布局技巧）。
7. `npm run build`（或项目前端构建）必须过。有浏览器工具则打开该页核对清单。
8. `verification-gate`。未完成则 `handoff.md`。

## 目视清单（最少）

- [ ] 主态
- [ ] 窄屏/目标断点
- [ ] 空态或长文本是否撑破
- [ ] 对比度仍可读（不要为「好看」把字变灰到看不清）
- [ ] 未改到范围外的页面

## 门禁

G0 G8 G9 必守。无契约变化 → 不写假 spec。禁止顺手改业务分支。
