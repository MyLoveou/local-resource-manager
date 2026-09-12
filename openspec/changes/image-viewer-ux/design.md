# 设计 · image-viewer-ux

与 `docs/requirements/features/image-viewer-ux/实现方案.md` 同一套。

## Context

当前 `ImageViewerOverlay` 为 `position:fixed; inset:40px 0 0 0`，再在罩内复制 InfoPanel，顶条放关闭/上一张/下一张。Viewer.js 默认 transition + `update()` 切图，窗口 resize 重排整窗。

## Decisions

| 决策 | 选择 | 不选 |
|------|------|------|
| 占位 | 只盖 `main` | 继续全应用罩；中央小对话框 |
| 元数据 | 壳右侧 InfoPanel 不卸 | 罩内再挂一块左栏 |
| 导航 | 图上：右上关闭、左右中部切张 | 顶条三个文字按钮 |
| 动作区 | 保存/编辑/回收站 + 「更多」 | 一排 8+ 按钮 |
| 库 | 仍 Viewer.js，封装内关动画、resize rAF | 本轮换 PhotoSwipe |

## Risks

- Viewer.js 拖拽若仍用 layout 而非 transform，封装只能减轻不能根治；仍卡则下一切片换库（需另拍板）。
