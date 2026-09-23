# 提案 · image-viewer-ux

> 修订 `image-consume` 的查看器壳与信息栏动作区。不改 IPC / REST。

## Why

落地后的全窗覆盖层难看、拖拽卡、窗口缩放掉帧；查看器盖住整块软件；信息栏按钮挤成一排；关闭/上一张/下一张在顶条，不像看图。

## What Changes

- 查看器**只盖住中间 `main`（网格）**，不盖顶栏、不盖侧栏菜单、**不盖右侧信息栏**。看图时仍用同一份 InfoPanel。
- 关闭在图区右上；上一张/下一张在图左右中部。
- 信息栏主按钮只留保存 / 编辑 / 回收站（或恢复）；打开位置与外部应用等收入「更多」。
- 封装内关掉 Viewer 过渡动画；切图不整实例重建；尺寸变化用 rAF 调 `resize`。本轮**不换** Viewer.js。

**BREAKING：** 无 API。交互上不再「覆盖层内再复制一块左栏」。

明确不交付：换看图库、视频、画廊、重做整页视觉系统。

## Capabilities

### Modified Capabilities

- `desktop-image-viewer`：覆盖范围改为 main；导航按钮落在图上；手势须跟手

### New Capabilities

- 无

## Impact

- 仅 renderer：`App.vue`、`ImageViewerOverlay`、`ImageViewerHost`、封装、`InfoPanel` 底部动作
- 修订 D-20260912-17 的「覆盖层左栏复制 InfoPanel」
