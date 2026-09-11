## Why

信息栏嵌在 ResourceBrowser 里，首页没有右栏；选中态是组件局部 ref，store 闲置。工具栏和快捷键以后无法共享「当前资源」，三栏布局也无法在所有路由上保持稳定。

## What Changes

- 应用壳层固定为顶栏 + 左菜单 + 主区 + 右信息栏。
- 当前选中 id 进入 Pinia `selection` store；卡片点击写入 store。
- InfoPanel 从 store 读 id 并拉取详情；无选中时显示空态（不再要求必填 resourceId）。
- ResourceBrowser 不再内嵌 InfoPanel。
- 删除走已有 `useResourceHandle`，成功后清除选中（编辑表单仍不在本 change）。

不改后端契约，不引入 `/v1`。

## Capabilities

### New Capabilities

- `desktop-shell-selection`: 桌面壳层三栏与跨页面的资源选中态

### Modified Capabilities

- （无）

## Impact

- `App.vue`、`InfoPanel`、`ResourceBrowser`、`stores/selection.ts`
- 可能微调 Image/Video 页面容器样式
