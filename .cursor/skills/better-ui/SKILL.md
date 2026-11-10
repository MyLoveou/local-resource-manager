---
name: better-ui
description: >-
  抛光表面、图标和动效：同心圆角、光学对齐、阴影、图标状态、按压缩放。触发：更好看、
  抛光、圆角、阴影、微交互、悬停、图标、feels off、better-ui。
  交互已经坏了时，抛光不能压过修复。先定观感走 project-spec-design，只改样式的门禁走 project-spec-style。
origin: jakubkrehel/skills（MIT，Jakub Krehel）；配方保留原文数值
---

# 界面抛光

管表面、图标和动效的具体数值。底层交互必须先是对的。一条抛光发现不能压过一个坏掉的交互。

下面标成精确的值就按原值做：`cubic-bezier(0.2, 0, 0, 1)` 不是 `cubic-bezier(0.4, 0, 0.2, 1)`，`0.96` 不是 `0.95`。光学微调，以及内边距超过 `24px` 后不再套同心圆角，这两处是起点，用眼睛判断。

保留项目的组件库、token 和密度。本技能没给数值的地方，跟项目已有的动效语言。项目有意且统一的约定（例如全站不用阴影）是偏好，不是发现。同一细节在项目里做成两种，才是发现。

换行、字体渲染、等宽数字和字距归 `better-typography`。命中区域、键盘、ARIA 和减弱动效的硬要求归 `fixing-accessibility`。分组、区块间距、断点和空间上的 RTL 归 `better-layout`，方向性图标的镜像除外。颜色用项目已有色板；对比度是否通过归 `fixing-accessibility`。卡顿归 `fixing-motion-performance`。

CSS 配方在同目录 `references/`，原文英文，数值不要意译。配方里写的 `better-accessibility` 就是本库的 `fixing-accessibility`。

## 外圆角等于内圆角加内边距

嵌套表面有均匀、可见的内缩时，外圆角 = 内圆角 + 内边距 + 边框宽度。内边距超过 `24px`，或有意不对称时，当成两层独立表面，各用自己的圆角 token。见 [references/surfaces.md](references/surfaces.md)。

## 几何居中看起来歪，就光学对齐

按钮靠图标的一侧少 `2px` 内边距。播放三角往尖端挪。不对称字形改在 SVG 里。见 [references/surfaces.md](references/surfaces.md)。

## 阴影表示高度，边框表示结构

边框若只为了制造深度，改成多层透明 `box-shadow`。分隔线、表格单元格、选中态、表单输入保留边框。输入边界需要 3:1 的非文字对比度。焦点环归 `fixing-accessibility`。

强制颜色模式会去掉全部 `box-shadow`。阴影环旁边保留 `border: 1px solid transparent`，那种模式仍有边缘。见 [references/surfaces.md](references/surfaces.md)。

## 内容图片用纯黑或纯白描边

内容图片用内缩 `1px` 的 `1px` 描边。亮色 `oklch(0 0 0 / 0.1)`，暗色 `oklch(1 0 0 / 0.1)`。不要用调色板里的近黑、带色的中性色或强调色，边缘会脏。透明作品（标志、插画）跳过。见 [references/surfaces.md](references/surfaces.md)。

## 交互状态用过渡，不用关键帧

交互状态用 CSS transition，或动效库里能在中途反向时重新瞄准的弹簧。关键帧时间轴固定，不能反向，只留给只播一次的序列。见 [references/animations.md](references/animations.md)。

## 按下缩放到 0.96

按下的按钮在 `150ms`、`ease-out` 内缩到 `0.96`。禁用的不缩放。会干扰的地方用组件已有变体或一个静态开关关掉。见 [references/animations.md](references/animations.md)。

## 高频交互立刻响应

按键、行悬停、页签切换：立刻反馈，或只在 `opacity` / `background-color` 上做不超过 `150ms` 的过渡。有表现力的动效留给少见时刻：视图第一次出现、成功、空状态。

每个有动画的状态变化都要留下静态线索：颜色、图标或文字。动效不能是唯一反馈。

## 动效服从减弱动效

位移、缩放和模糊只在 `prefers-reduced-motion: no-preference` 下发生。减弱动效时改成透明度交叉淡化，不要把元素瞬间拿掉。要求本身归 `fixing-accessibility`。见 [references/animations.md](references/animations.md)。

## 少见的入场错开 100ms

入场要靠顺序表达层级时，拆成语义块（标题、说明、操作），彼此错开 `100ms`。每块用透明度、`4px` 模糊和 `12px` 的 `translateY`，`300ms`、`ease-out`。日常交互不错开。见 [references/enter-exit.md](references/enter-exit.md)。

## 退出比进入更短更小

退出：透明度、`4px` 模糊、固定 `-12px` 的 `translateY`，`150ms`、`ease-out`。不要滑出整个容器高度。只有目的地有意义时才完全滑出，例如抽屉关上。动效不增加信息时直接移除。见 [references/enter-exit.md](references/enter-exit.md)。

## 状态切换的首次渲染不要动画

包住状态切换的 `AnimatePresence` 设 `initial={false}`，默认态不要在挂载时再演一遍。有意的入场（例如错开的首屏）不要加这个。见 [references/animations.md](references/animations.md)。

## 上下文图标按精确值交叉淡化

少见的图标切换（播放/暂停、复制/已复制）做交叉淡化。缩放 `0.25` 到 `1`，透明度 `0` 到 `1`，模糊 `4px` 到 `0`。有动效库时用 `{ type: "spring", duration: 0.3, bounce: 0 }`，`bounce` 永远是 `0`。没有库时两个图标都留在 DOM 里，`300ms`、`cubic-bezier(0.2, 0, 0, 1)`。

页签图标切换，以及行悬停才出现的操作，归「高频交互立刻响应」。见 [references/icon-transitions.md](references/icon-transitions.md)。

## 换主题时关掉过渡

换主题时关掉全部过渡，强制刷新样式，下一帧再恢复。否则所有颜色一起过渡，切换会糊。见 [references/animations.md](references/animations.md)。

## 只过渡真正变化的属性

写明属性，例如 `transition-property: scale, opacity`。不要 `all`。见 [references/performance.md](references/performance.md)。

## will-change 写动画的那个属性

只有看到首帧卡顿才加。`scale` 就写 `scale`，`transform` 就写 `transform`。只限 transform 属性、`opacity` 和 `filter`。不要 `all`。见 [references/performance.md](references/performance.md)。

## 悬停效果只给真的能悬停的指针

只悬停才有的样式放在 `@media (hover: hover)` 里。触摸上 `:hover` 会在点按后粘住，看起来像选中。Tailwind 4 的 `hover:` 已经包在这个查询里，Tailwind 3 没有。控件自己画按下态时，设 `-webkit-tap-highlight-color: transparent`，避免再叠一层灰闪。

## 浮层里的滚动不要带动页面

可滚动的对话框、抽屉、菜单和侧栏加 `overscroll-behavior: contain`。

## 图标笔画跟旁边文字的字重

字重 400 约 `1.5px`，700 约 `2.5px`。一块表面只用一套图标库。表、尺寸和网格见 [references/icons.md](references/icons.md)。

## 一个 SVG，靠颜色区分状态

图标用 `currentColor`。悬停、选中、禁用来自 CSS 颜色和透明度，不要换一套资源。默认描边，激活用填充。`dir="rtl"` 时只镜像含义跟阅读方向走的图标。见 [references/icons.md](references/icons.md)。

## 收尾对照

| 看到 | 改成 |
| --- | --- |
| 有内边距的父子圆角相同 | 外圆角加上内边距 |
| `box-shadow: 0 0 0 1px` 旁边没有 `border` | `border: 1px solid transparent` |
| 图片上用 slate、zinc 或十六进制描边 | 亮色黑 10%，暗色白 10% |
| `transition: all` | 写明变化的属性 |
| 在 `:hover`、`.open` 等切换类上用 `animation` | 改成同属性的 transition |
| 按下缩放到 `0.95` 或更小 | `0.96` |
| 按下缩放没有排除禁用 | `:not(:disabled):active` 或等价写法 |
| `bounce` 不是 `0` | `bounce: 0` |
| 基样式 `opacity: 0`，只靠 animation 露出来 | 隐藏放进 `from`，`animation-fill-mode: both` |
| 位移、缩放、滤镜没有减弱动效 | 守门；减弱时只做透明度交叉淡化 |
| 有颜色过渡和主题开关，但切换时没关掉过渡 | 用换主题抑制配方 |
| `will-change: all`，或元素从不动画却写了 will-change | 写明属性，或删掉 |
| 图标 SVG 里写死 `fill` / `stroke` 颜色 | `currentColor` |
| 普通 `:hover` 或 Tailwind 3 的 `hover:` 不在 `@media (hover: hover)` 里 | 包进该查询 |
| 对话框、抽屉、菜单可滚动但没有 overscroll 限制 | `overscroll-behavior: contain` |

## 报告

**严重度。** `HIGH`：交互坏了。关键帧切换不能反向、触摸上悬停粘住、动效无视 `prefers-reduced-motion`、状态变化只靠动效。`MEDIUM`：表面、图标或动效可见地不一致。`LOW`：孤立抛光。

**验证。** 没有浏览器时，从代码读每个状态（悬停、按下、选中、加载、空）的时长和缓动。有浏览器时走一遍，并在动画面板里用 10% 速度回放。没跑的检查写「未验证」。

**格式。** 按违反的原则分组，按严重度排序。一个根因一行，列出它出现的每一处：

| 严重度 | 位置 | 改前 | 改后 | 原因 |
| --- | --- | --- | --- | --- |

位置写 `路径:行号`。原因写原则和用户影响。

还有 `HIGH` 就以「阻断」结束，否则「通过」，其余留在表里。没看过的范围不要写通过。没有发现时写「没有可执行的界面抛光发现」，并写验证情况。
