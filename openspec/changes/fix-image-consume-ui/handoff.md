# 跨会话续作 · fix-image-consume-ui

## 状态

- change：`fix-image-consume-ui`
- 阶段：`待手工验`
- 最后更新：2026-09-12

## 已做

- 去掉 Teleport：列表 `InfoPanel v-if="!viewerOpen"`，查看器左侧 `InfoPanel v-if="visible"`。
- Viewer 源图隐藏、`fullscreen: false`、单实例，只留一层画布。
- `pnpm --filter desktop typecheck` 通过。

## 下一步

重启渲染后手工 R1–R3。未授权不 commit。
