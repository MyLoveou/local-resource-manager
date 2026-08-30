# 组件目录（独立 · 通用可复用）

与页面/布局分离的**独立组件目录**，仅含展示性、可复用的组件（不直接依赖业务 store）。

规划组件：
- `VirtualGrid.vue` — 卡片网格虚拟滚动（@tanstack/vue-virtual）
- `ResourceCard.vue` — 资源卡片（缩略图/标题/关键元数据）
- `MetadataPanel.vue` — 右侧元数据面板
- `SettingsModal.vue` — 设置弹窗
- `Icon.vue` — 图标封装（@iconify/vue）
- `EmptyState.vue` — 空态 / 加载态
