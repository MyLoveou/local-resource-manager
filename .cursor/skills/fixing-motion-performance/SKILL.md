---
name: fixing-motion-performance
description: >-
  审计并修动画性能：布局抖动、合成器属性、滚动联动、模糊。触发：动画卡、
  过渡顿、滚动动画、模糊、will-change、fixing-motion-performance。
  本库默认不加动画；用户没要求动效时不要用本技能去加。
origin: ibelick/ui-skills（MIT，Julien Thibeaut）
---

# 修动效性能

在项目已有的动画体系里修，不要换动画库，除非用户明确要求。不要在同一个组件里混两套动画 API。

抛光层面的时长、按压缩放和减弱动效见 `better-ui`。这里管贵不贵、会不会掉帧。

## 怎么用

在这些时候套用：改 CSS、WAAPI、Motion、`requestAnimationFrame`、GSAP；修卡顿；做滚动联动或滚动显现；动画布局、滤镜、遮罩、渐变或 CSS 变量；审查 `will-change`、transform、测量。

点名文件时输出：引用原片段、一句话说明影响、一处具体改法。非默认选择要写明理由：面积、时长，或交互确实需要。

## 渲染成本

- 合成：`transform`、`opacity`
- 绘制：颜色、边框、渐变、遮罩、图片、滤镜
- 布局：尺寸、位置、流、grid、flex

| 优先级 | 类别 | 影响 |
|--------|------|------|
| 1 | 禁止模式 | 关键 |
| 2 | 选机制 | 关键 |
| 3 | 测量 | 高 |
| 4 | 滚动 | 高 |
| 5 | 绘制 | 中高 |
| 6 | 图层 | 中 |
| 7 | 模糊与滤镜 | 中 |
| 8 | 视图过渡 | 低 |
| 9 | 改动边界 | 关键 |

## 规则

1. **禁止**：同一帧里交替读布局和写布局。不要在大面积上连续动画布局。不要用 `scrollTop`、`scrollY` 或 scroll 事件驱动动画。`requestAnimationFrame` 循环必须有停止条件。不要让多套动画系统各自测量或改布局。
2. **机制**：运动默认 `transform` 和 `opacity`。只有交互需要时才用 JS 驱动。绘制或布局动画只允许在很小的孤立元素上。一次性效果比连续运动更容易接受。优先把手法降级，而不是把动效整个删掉。
3. **测量**：先量一次，再用 transform 或 opacity 动画。先批量读 DOM，再写。动画过程中不要反复读布局。看起来像布局变化的过渡，优先 FLIP。
4. **滚动**：滚动联动优先用 Scroll / View Timeline（环境支持时）。显隐和暂停用 `IntersectionObserver`。不要轮询滚动位置。离开视口就暂停。滚动联动不能让大面积持续触发布局或绘制。
5. **绘制**：只允许在小元素上动画会触发绘制的属性。不要在大容器上这么做。不要用 CSS 变量去动画 transform、opacity 或位置。不要动画会被继承的 CSS 变量。
6. **图层**：合成器动画需要图层提升，不能假设已经提升。`will-change` 临时、精确地加。避免又多又大的提升层。性能要紧时用工具核对图层。
7. **模糊**：模糊动画不超过 `8px`，只用于短的一次性效果。不要连续模糊，不要在大面积上模糊。优先 opacity 和 translate。
8. **视图过渡**：只用于导航级变化。交互密集的界面不要用。需要可打断、可取消时不要用。尺寸变化可能触发布局。
9. **边界**：不迁移动画库。规则落在现有体系里。

## 常见改法

```css
/* 用 transform，不要动画 width */
.panel { transition: transform 0.3s; }

/* 滚动显现用滚动时间线，不要监听 scroll */
.reveal { animation: fade-in linear; animation-timeline: view(); }
```

```js
// 先读完再写（FLIP），不要边读布局边改 left
const first = el.getBoundingClientRect();
el.classList.add('moved');
const last = el.getBoundingClientRect();
el.style.transform = `translateX(${first.left - last.left}px)`;
requestAnimationFrame(() => {
  el.style.transition = 'transform 0.3s';
  el.style.transform = '';
});
```

先执行禁止模式和边界。审查时给可执行的替代，少讲原理。
