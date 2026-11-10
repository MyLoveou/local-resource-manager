# 跨功能界面规格

> 放**跨功能**的界面规格：布局骨架、全局交互模式、视觉令牌与状态约定。
> 单能力的界面画法与视觉方向不放这里（见下表分工）。

## 分工

| 内容 | 落点 |
|------|------|
| 跨功能布局/交互/令牌规格 | 本目录 |
| 单能力的界面方向、观感 | `docs/requirements/features/<id>/界面方向.md` |
| 单能力的交互与状态设计（L2） | `docs/requirements/features/<id>/设计.md` |
| 全局提示（Toast/Push/Confirm/Loading） | [`../design/04-全局提示系统.md`](../design/04-全局提示系统.md) |
| 单能力实现方案（组件与文件清单） | `docs/requirements/features/<id>/实现方案.md` |

## 已有界面真源

| 文档 | 内容 |
|------|------|
| [`../requirements/features/lrm-ui.md`](../requirements/features/lrm-ui.md) | 主需求：三栏布局与页面结构（已定稿） |
| [`../requirements/features/wch-ui.md`](../requirements/features/wch-ui.md) | 工作台增量 UI（草案） |
| [`../requirements/features/scrape-confirm-ux/界面方向.md`](../requirements/features/scrape-confirm-ux/界面方向.md) | 刮削确认分栏 |
| [`../requirements/features/ui-shell-redesign/设计.md`](../requirements/features/ui-shell-redesign/设计.md) | Shell、导航分组、顶部工具组、选中态操作栏、AI 中心入口 |

## 待补规格

后续新界面规格用 `<name>.md` 落本目录，并在上表登记；与代码不一致时先改文档（G4）。
