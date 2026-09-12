# 跨会话续作 · image-viewer-ux

## 状态

- change：`image-viewer-ux`
- 阶段：`待手工验`
- 最后更新：2026-09-12

## 已做

- Overlay 只盖 `main`；右侧 InfoPanel 常驻。
- 关闭在图右上；切张在图左右中部。
- 信息栏「更多」收打开位置/外部应用/换封面/字幕。
- Viewer 封装关过渡、切图不 `update`、ResizeObserver + rAF。
- **拉伸**：去掉 canvas `max-width:90%` 与脚本宽高冲突；源图不再压成 1×1。
- typecheck 通过。决策 D-20260912-18。

## 下一步

手工 U1–U4（占位、按钮位置、拖拽/窗口缩放、更多菜单）。未授权不 commit。
