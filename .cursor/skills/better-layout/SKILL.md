---
name: better-layout
description: >-
  定分组、对齐、阅读顺序和响应式结构，让布局在变窄、翻译和镜像后仍然成立。
  触发：布局、对齐、间距、分组、响应式、RTL、折行、better-layout。
  先定观感走 project-spec-design，只改样式的门禁走 project-spec-style。
origin: jakubkrehel/skills（MIT，Jakub Krehel）；配方保留原文数值
---

# 布局

定分组、对齐、间距和响应式结构，再用变窄、加长文案和 RTL 镜像去压它。

改动写进项目自己的样式系统。下面的像素只在项目没有间距刻度或密度系统时使用；有 token 就用 token。发现必须能指出来：裁切、重叠、镜像坏了、一组被读错。数值和这些起点不同，本身不是发现。

命中区域和焦点归 `fixing-accessibility`。圆角、阴影和动画归 `better-ui`。行长、字距和截断手法归 `better-typography`。文案用词不在这些技能里。

CSS 配方在 `references/`，原文英文，数值不要意译。

## 用空白分组，少用线

先靠空白，其次靠底色块，分隔线最后，而且只在空白撑不起结构时用。组与组的间隙至少是组内的 2 倍：组内 `8px`，组间至少 `16px`。见 [references/grouping-and-alignment.md](references/grouping-and-alignment.md)。

## 控件要和内容区分开

每个可交互元素要有底色、边框、下划线，或稳定的放置区（例如工具栏）。控件长得和旁边的静态文字一样，就不像控件。见 [references/grouping-and-alignment.md](references/grouping-and-alignment.md)。

## 对齐到共用的边

选少数几条对齐边，全部贴上去。每一层嵌套用项目的一个间距步进。没有刻度时，`16px` 是可用的默认。见 [references/grouping-and-alignment.md](references/grouping-and-alignment.md)。

## 会镜像的布局用逻辑属性

方向相关的写成起始侧和结束侧：`margin-inline-start`、`padding-inline-end`、`inset-inline-start`、`text-align: start`。物理的 left / right 留给物理几何，例如安全区。对照表见 [references/grouping-and-alignment.md](references/grouping-and-alignment.md)。

## 按重要性排序

最重要的内容靠近顶部和起始侧。一行里，识别内容在前，元数据和操作在后。视觉顺序和 DOM 顺序一致。不要用 `order`、`row-reverse` 或网格摆放把内容挪出源码顺序。见 [references/grouping-and-alignment.md](references/grouping-and-alignment.md)。

## 一个视图一个主操作

每个视图一个主操作。次要操作超过 3 个就收进菜单。宁可短视图链到下一层，也不要一个长视图把一切摊在顶层。主操作的颜色用项目已有的强调色，不另造配色。

## 藏起来的内容要有线索

屏外或折叠的每一块内容都要有看得见的提示。用项目既有的提示；或让下一项从滚动边缘探出 `16–32px`；或给一个展开控件。

用户需要的截断值必须能回到全文：展开、详情，或键盘也能打开的提示。截断的 CSS 手法归 `better-typography`。见 [references/spacing-and-adaptivity.md](references/spacing-and-adaptivity.md)。

## 没有边框的控件要留更多空隙

没有既定密度系统时，相邻的有边框或有填充控件从 `12px` 起。无边框的文字和图标控件，可见字形之间留 `24px`，算上按钮自己的内边距。紧凑布局可以更小，但命中区域不能重叠，控件仍要能区分。见 [references/spacing-and-adaptivity.md](references/spacing-and-adaptivity.md)。

## 按钮从边缘缩进

内容布局里，通栏按钮留在版心内。移动端行向大约从 `16px` 起。贴边操作只在它符合平台既有框架、算了安全区、并且和系统界面分得开时才用。见 [references/spacing-and-adaptivity.md](references/spacing-and-adaptivity.md)。

## 内容出血，控件浮在版心里

背景和媒体可以伸到视口边。控件和文字留在版心和安全区内。`env(safe-area-inset-*)` 只有视口 meta 含 `viewport-fit=cover` 时才非零。

内容从粘性顶栏下面滚过。把 `scroll-padding-block-start` 设成顶栏高度，锚点和焦点不要落在顶栏底下。见 [references/spacing-and-adaptivity.md](references/spacing-and-adaptivity.md)。

## 结构撑不住了再断

断点来自内容，不来自设备预设。展开的布局能放下就保持，放不下再收。组件级适配优先容器查询。先测支持范围内最小和最大的尺寸。见 [references/spacing-and-adaptivity.md](references/spacing-and-adaptivity.md)。

## 为变长和裁切留余地

翻译会变长，短字符串按比例涨得更多，所以一个词的按钮最危险。文字容器用 `max-width` 和 `min-height`，不要固定宽高，行允许换行。用伪本地化和一种长文案语言（例如德文）试。

关键操作不能放在变窄、缩放或滚动就会裁掉的地方。留在正常流或稳定的框架里。见 [references/spacing-and-adaptivity.md](references/spacing-and-adaptivity.md)。

## 收尾对照

| 看到 | 改成 |
| --- | --- |
| `1fr` 轨道或 flex 子项里的长文本或宽表格溢出 | 轨道 `minmax(0, 1fr)`，flex 子项 `min-width: 0` |
| `width: 100vw` | `width: 100%`。`100vw` 含滚动条，桌面会横向滚 |
| 全高移动面板用 `100vh` | `100dvh`，避免工具栏和键盘盖住底部 |
| 装文字的盒子用定长 `height` | `min-height`，或 `max-height` 加 `overflow-y: auto` |
| 可复用组件里写死 `@media (max-width)` | 在父级用 `@container` |
| flex 项、inline-block 或未定宽的绝对元素上设 `container-type: inline-size` | 给确定宽度，否则收缩到零 |
| 用了 `env(safe-area-inset-*)` 但视口 meta 没有 `viewport-fit=cover` | 加上，否则内边距是 0 |
| 逻辑 inset 和 `safe-area-inset-left/right` 混用 | 物理 left/right 配对应 inset，并写 `[dir="rtl"]` 覆盖 |
| 会镜像的界面用 `float: left` | `float: inline-start` |
| 会镜像的界面用 `translateX` 或 `background-position: left` | 加 `[dir="rtl"]` 覆盖，它们没有逻辑形式 |
| 粘性顶栏没有 `scroll-padding-block-start` | 设成顶栏高度 |

## 报告

**严重度。** `HIGH`：在支持的视口上挡住内容或操作。320px 宽或 200% 缩放下的裁切和重叠永远是 `HIGH`。截断了却回不到全文，或滚出屏幕、折在展开控件后面却没有可见线索，也是。`MEDIUM`：伤害层级、阅读顺序或适配。`LOW`：孤立的对齐或间距。

**验证。** 没有浏览器时核对逻辑属性、容器查询和媒体查询是否覆盖支持的视口、DOM 顺序是否等于视觉顺序。有浏览器时走每个支持宽度、320px、200% 缩放和 RTL 镜像。没跑的写「未验证」。

**格式。** 按原则分组，按严重度排序，一个根因一行：

| 严重度 | 位置 | 改前 | 改后 | 原因 |
| --- | --- | --- | --- | --- |

还有 `HIGH` 就以「阻断」结束，否则「通过」。没看过的范围不要写通过。没有发现时写「没有可执行的布局发现」，并写验证情况。
