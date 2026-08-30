# UI 层（布局 + 样式，非页面）

页面的**骨架与外观**，不含业务页面逻辑。

- `layouts/` — 三栏布局组件（`MenuBar` 左菜单 / `ToolBar` 顶栏 / `InfoPanel` 元数据面板）
- `styles/` — 全局样式（less 主题变量 `variables.less` + 基础 `global.css`）

> 页面（路由组件）→ 顶层 `views/`；通用可复用组件 → `components/`；逻辑 → `hooks/`。

依赖方向：UI → application（业务层）
