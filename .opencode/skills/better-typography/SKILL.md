---
name: better-typography
description: >-
  设定并审查文字如何渲染：字级、行高、字重、换行、截断、标点。触发：字体、字号、
  行高、截断、换行、tabular-nums、typography、better-typography。
  先定观感走 project-spec-design，只改样式的门禁走 project-spec-style。
origin: jakubkrehel/skills（MIT，Jakub Krehel）；配方保留原文数值
---

# 字体

管文字怎么渲染：字级、间距、字体加载、换行和标点。改动写进项目自己的样式系统。声明和 Tailwind 工具类的对照在 [references/css-cheat-sheet.md](references/css-cheat-sheet.md)，项目不用 Tailwind 时看左边的 CSS。

用词不在这些技能里。标题的语义层级归 `fixing-accessibility`。空间上的 RTL 归 `better-layout`。对比度是否通过归 `fixing-accessibility`，色值用项目色板。下划线以外的动效归 `better-ui`。

配方原文英文，数值不要意译。

## 有的值是硬的，有的只是启发

漏了就是发现：无单位行高、`18px` 以下字重至少 `400`、长文每行 60–75 字、iOS 输入至少 `16px`、会变化的数字用 `tabular-nums`。

字距、字体搭配和字级比例是启发。只在它们打破项目自己的字级时才报。任务没要求换字体时，不要提议新字体，收费的免费的都不要。

## 少用字体、字号和字重

很少超过三种字体；营销页可以比应用多。层级靠字重和字号，多一个就稀一点。搭配要有对比：衬线标题加无衬线正文是有意的，两个几乎一样的无衬线是失误。

`18px` 以下用 `400` 或更重。`100`–`300` 留到 `28px` 及以上，并且对照背景检查。分类、Display 与 Text 切分、格式和回退栈见 [references/choosing-fonts.md](references/choosing-fonts.md)。

## 加载设计真正用到的字重

浏览器会合成家族没提供的字重或样式，字形会变形。设计用到的都要加载。只有核对过回退栈之后，才关掉合成，而且只关不想要的那一种。见 [references/variable-fonts-and-opentype.md](references/variable-fonts-and-opentype.md)。

## 有 CSS 属性就用属性

`font-weight: 650`，不要 `font-variation-settings: "wght" 650`。`font-variant-numeric: tabular-nums`，不要 `font-feature-settings: "tnum" 1`。属性在非可变字体回退时仍然有效。

`font-optical-sizing` 保持默认 `auto`。只有设计有意把光学尺寸和字号拆开时才写死 `"opsz"`。原始标签留给没有对应属性的自定义轴，例如 `"GRAD" 80`、`"ss01" 1`。见 [references/variable-fonts-and-opentype.md](references/variable-fonts-and-opentype.md)。

## 用带语义的小字级

字号尽量少，每个字号配好行高和字重，一个角色一次决定，而不是三个旋钮。

一个人用、规则清楚时，`text-sm` 这种默认名可以。协作时按用途命名（`text-body-sm`），规则才能留下来。起步刻度见 [references/spacing-and-sizing.md](references/spacing-and-sizing.md)。

## 标题字号随级别下降

标题级别对应字级上逐级变小的台阶，下级不能压过上级。台阶不够时，深层可以同号，但字重或字距要能区分。标题不要小于正文，除非是有意的眉题。见 [references/spacing-and-sizing.md](references/spacing-and-sizing.md)。

## 行高按角色

展示文字 `1.1`，标题 `1.2`–`1.3`，正文 `1.5`–`1.6`。用无单位值，行高才能跟字号一起缩放。固定 `24px` 不会。

紧行高只给短文字。会折到三行及以上的，至少 `1.4`，即使那一行高度很紧。见 [references/spacing-and-sizing.md](references/spacing-and-sizing.md)。

## 字距按字号

`24px` 及以上的标题用 `-0.01em` 到 `-0.02em`。`14px` 及以下的全大写标签用 `0.05em`。正文保持 `0`。用 `em`，字距才跟字号走。

字偶距是字体自带的，默认开着。`font-kerning: none` 从来不是修法。

## 限制行长

长文每行 60–75 字。单位不限，但必须有上限，并且落在这个范围。见 [references/wrapping-and-punctuation.md](references/wrapping-and-punctuation.md)。

## 有意换行

- `text-wrap: balance` 用于标题和短说明。不要用在段落上。Chromium 超过六行会忽略它。
- `text-wrap: pretty` 避免最后一行只剩一个词。段落可以用，含长文。
- 长单词、链接或 ID 可能撑破容器时用 `overflow-wrap: break-word`。
- 标签和徽章换行会难看时用 `white-space: nowrap`。

界面文字用 `text-align: start`。`justify` 只属于特定的编辑排版。

## 会变化的数字用等宽数字

计时、计数、价格和数字列用 `font-variant-numeric: tabular-nums`，每位一样宽，数字变化时不跳动。散文里的数字保持比例体。

## 截断要能回去

一行：`overflow: hidden`、`text-overflow: ellipsis`、`white-space: nowrap`（Tailwind 的 `truncate`）。多行：`display: -webkit-box`、`-webkit-box-orient: vertical`、`-webkit-line-clamp`、`overflow: hidden`（Tailwind 的 `line-clamp-*`）。

截断的值必须能回到全文，这条归 `better-layout`。

## 原文用自然大小写，渲染用排印标点

大小写用 `text-transform`，不要把文案存成全大写，否则改设计就要改文案。

渲染文本用排印字符，不用键盘替代：弯引号、短破折号、省略号、不换行空格。见 [references/wrapping-and-punctuation.md](references/wrapping-and-punctuation.md)。代码保持直引号。

## 下划线跟字体走

`text-underline-position: from-font`，`text-decoration-thickness: from-font`，或手调偏移和粗细。点状 `text-decoration-style` 表示这个词还有额外信息，例如缩写或术语。见 [references/details-and-accessibility.md](references/details-and-accessibility.md)。

真下划线里只有颜色能稳定地做动画。其他下划线动画需要单独元素，动效归 `better-ui`。

## 移动端输入至少 16px

iOS Safari 会在输入文字小于 `16px` 时放大整页。两种修法都保住 `16px`，外观不同，先问设计要哪一种：

- 小屏把输入放大（例如小屏 `16px`、更大屏再回到设计字号）。小屏外观会变。
- 保持 `font-size: 16px`，用 `transform: scale()` 画出想要的大小。各视口看起来一致，维护成本更高。

占位符和光标见 [references/details-and-accessibility.md](references/details-and-accessibility.md)。

## 字号下限

长文正文从 `16px`（浏览器默认）起。离开它要能说出原因：字体偏小、行长很窄，或这是高密度的专业工具。

界面文字可以更小。输入和菜单从 `14px` 起，说明从 `13px` 起，很少低于 `12px`。`font-size` 用 `rem`，读者自己的浏览器字号仍然生效。见 [references/spacing-and-sizing.md](references/spacing-and-sizing.md)。

## 字体平滑只加在根上

`-webkit-font-smoothing: antialiased` 和 `-moz-osx-font-smoothing: grayscale` 只加在根上一次。不要每个组件加。Tailwind 的 `antialiased` 两个都设了。

## 语言和双向文字

设置 `lang`，浏览器和辅助技术才能选对引号、断词和读音。文档设 `dir`，方向变化的地方也设。混合方向的值用 `<bdi>` 包住，不要手工重排数字。见 [references/wrapping-and-punctuation.md](references/wrapping-and-punctuation.md)。

## 紧容器里修剪文字盒

按钮和徽章里，字体在字母上下留的空间会让文字看起来偏下。`text-box: trim-both cap alphabetic` 作为渐进增强。见 [references/spacing-and-sizing.md](references/spacing-and-sizing.md)。

## 装饰文字用 CSS，不用图片

首字下沉、渐变字、描边字和文字阴影用 CSS，文字才能选中和搜索。见 [references/details-and-accessibility.md](references/details-and-accessibility.md)。

## 有用的文字默认可选

文字默认可选。`::selection` 可以带上品牌，只要选中组合仍然可读。见 [references/details-and-accessibility.md](references/details-and-accessibility.md)。

`user-select: none` 只放在拖拽或手势表面上，误选会干扰操作的时候。不要铺满界面，也不要因为按钮文字能被选中就关掉。

## 收尾对照

| 看到 | 改成 |
| --- | --- |
| `font-weight` 在已加载的 `@font-face` 里没有对应字重 | 加载那一档，或改用家族提供的字重 |
| 正文或界面文字上 `font-synthesis: none` | 去掉；核对回退栈后只关不想要的长写法 |
| `font-variation-settings` 写了 `"wght"` 或 `"opsz"` | 改 `font-weight`；去掉 `"opsz"` 让光学尺寸保持自动 |
| `font-feature-settings: "tnum"` 或 `"zero"` | `font-variant-numeric: tabular-nums` 或 `slashed-zero` |
| `line-height` 用 `px` 或 `rem` | 无单位值 |
| 说明、卡片正文或会折行的文字用极紧行高 | `1.4` 或更大 |
| `letter-spacing` 用 `px` | 改成 `em` |
| 正文字号用 `px` | `rem` |
| `18px` 以下用 `100`–`300` | `400` 或更重 |
| 段落上 `text-wrap: balance` | `text-wrap: pretty` |
| 应用界面 `text-align: justify` | `text-align: start` |
| `-webkit-line-clamp` 没有 `display: -webkit-box` | 补上 `display: -webkit-box` 和 `-webkit-box-orient: vertical` |
| 计时、计数、价格或数字列没有等宽数字 | `font-variant-numeric: tabular-nums` |
| 渲染文案里的 `...`、`--` 或连字符范围 | `…`、长破折号或短破折号 |
| `text-decoration-skip-ink: none` | 去掉；改用 `text-underline-offset` 或 `from-font` |
| 输入是 `14px` 且没有移动端覆盖 | 用上面两种 16px 修法之一 |
| 组件里写了字体平滑 | 挪到根上 |
| 混合方向的名字、数字或 URL 没有 `<bdi>` 或 `dir` | 用 `<bdi>` 包住 |
| 布局根或文字容器上 `user-select: none` | 去掉；只留在拖拽或手势表面 |

## 报告

**严重度。** `HIGH`：文字读不了、截断后回不去、或在 320px 宽 / 200% 缩放下被裁切。后两条无论表面多小都是 `HIGH`。`MEDIUM`：字级系统或视觉标题层级坏了。`LOW`：孤立抛光。

**验证。** 没有浏览器时，按标题级别核对声明的字号和字重是否逐级下降，核对行高、单位和行长，用真实长度的字符串核对截断。有浏览器时比较计算值，再用真实内容改变视口，看换行、末行孤词和截断。没跑的写「未验证」。

**格式。** 按原则分组，按严重度排序，一个根因一行：

| 严重度 | 位置 | 改前 | 改后 | 原因 |
| --- | --- | --- | --- | --- |

还有 `HIGH` 就以「阻断」结束，否则「通过」。没看过的范围不要写通过。没有发现时写「没有可执行的字体发现」，并写验证情况。
