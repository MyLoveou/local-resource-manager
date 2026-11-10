---
name: baseline-ui
description: >-
  快速收拾界面俗套：间距、层级、字体和小布局。触发：界面不好看、收拾一下、
  防 AI 味、baseline-ui、快速抛光。先定观感仍走 project-spec-design，只改样式的门禁仍走 project-spec-style。
origin: ibelick/ui-skills（MIT，Julien Thibeaut）；按本库改成跟项目现有栈
---

# 界面底线

挡住常见的「生成式界面」：乱渐变、乱字距、主动加动画、空状态没有下一步。

先定这一页观感走 `project-spec-design`。只改样式的范围和构建门禁走 `project-spec-style`。本技能提供约束。分组与对齐见 `better-layout`，字见 `better-typography`，圆角阴影与微交互见 `better-ui`，键盘与焦点见 `fixing-accessibility`，动效卡顿见 `fixing-motion-performance`。

## 怎么用

- 做界面时套用下面的约束。
- 点名文件时：引用原片段、用一句话说明为何有问题、给出能落地的改法。

## 栈

- 项目已有 Tailwind 时，用它的默认刻度，除非已经有自定义值，或用户明确要求新值。
- 类名合并用项目里已有的工具。没有就不要为了本技能新造 `cn`。
- 需要 JavaScript 动画时，用项目已有的动效库。不要为了本技能安装 `motion/react`、`tw-animate-css` 或另一套原语。
- 默认不加动画。用户要求动效时，只动 `transform` 与 `opacity`。

## 组件

- 有键盘或焦点行为的控件，用项目里已有的可访问组件。
- 同一块交互里不要混两套组件原语。
- 项目没有现成原语时用原生元素。除非用户明确要求，不要手写焦点陷阱。
- 只有图标的按钮必须有可访问名称。

## 交互

- 破坏性或不可逆操作必须先确认。用项目已有的确认对话框；没有就用原生确认，不要新造一套对话框库。
- 加载态优先用结构骨架，而不是只转圈。
- 全屏高度用 `dvh`，不用 `vh` / `h-screen` 盖住移动端工具栏。
- 固定元素尊重 `safe-area-inset`。
- 错误显示在触发它的操作旁边。
- 不要禁止 `input` 或 `textarea` 粘贴。

## 动画

- 用户没要求就不要加动画。
- 只动画合成器属性（`transform`、`opacity`）。
- 不要动画布局属性（`width`、`height`、`top`、`left`、`margin`、`padding`）。
- 绘制属性（`background`、`color`）只允许出现在很小的局部，例如文字和图标。
- 入场用 `ease-out`。交互反馈不超过 `200ms`。
- 循环动画离开视口就暂停。尊重 `prefers-reduced-motion`。
- 不要自造缓动曲线，除非用户明确要求。
- 不要动画大图或整屏。

## 字体

- 标题用 `text-wrap: balance`，正文用 `text-wrap: pretty`。
- 会变化的数字用 `tabular-nums`。
- 密集界面可以截断，但截断必须能回到全文（见 `better-layout`）。
- 不要改 `letter-spacing`，除非用户明确要求。更细的字级规则见 `better-typography`。

## 布局

- `z-index` 用项目已有层级。没有就固定少数几档，不要写任意大数。
- 正方形在已使用 Tailwind 时用 `size-*`，否则宽高写成同一个值。

## 性能

- 不要在大面积上动画 `blur()` 或 `backdrop-filter`。
- `will-change` 只在动画进行时加，结束就去掉。
- 渲染时能算出来的，不要放进副作用（React 的 `useEffect`、Vue 的 `watch` 都算）。

## 外观

- 不要用渐变，除非用户明确要求。
- 不要用紫色或多色渐变，不要用发光当主要可点提示。
- 阴影用项目已有刻度；用 Tailwind 且没有自定义阴影时，用它的默认刻度。
- 空状态必须有一个明确的下一步。
- 一个视图只用一个强调色。
- 新颜色先用项目主题或已有色板。
