# 缺陷记录 · fix-image-consume-ui

## 复现

- 环境：Electron 桌面，`image-consume` 落地后
- 步骤：
  1. 打开图片页，单击选中一张图
  2. 再点同一张打开查看器
- 期望：列表页右侧始终有信息栏；查看器左信息栏、右**一层**嵌在右栏内的图
- 实际：
  1. 资源列表页元数据面板消失
  2. 出现两层图：一层占满软件窗口，一层较小可滚轮缩放
  3. 查看器内没有元数据面板
- 证据：用户手工复现（2026-09-12）

## 根因

- 路径：`App.vue` Teleport；`createInlineImageViewer.ts` 把 Viewer.js 源 `<img>` 与 `.viewer-container` 叠在一起，且 `fullscreen` 仍开
- 一句话原因：InfoPanel 被 Teleport 到空锚点，首屏目标可能尚未入 DOM，列表与覆盖层都丢面板；封装未藏源图，Viewer 再插一层画布，看起来像两套查看器
- 为何不是「新需求」：需求仍是「左元数据右看图」；这是实现错误

## 改动范围

| 路径 | 改什么 |
|------|--------|
| `apps/desktop/src/renderer/src/App.vue` | 去掉 Teleport；列表布局直接挂 InfoPanel |
| `apps/desktop/src/renderer/src/components/ImageViewerOverlay/index.vue` | 左侧直接挂 InfoPanel（与壳互斥只挂一份） |
| `apps/desktop/src/renderer/src/infrastructure/viewer/createInlineImageViewer.ts` | 单实例、藏源图、关闭 Viewer 全屏、容器限制在 host |
| `apps/desktop/src/renderer/src/components/ImageViewerHost/index.vue` | 源图不可见，只留一层 viewer 画布 |
| `docs/requirements/features/image-consume/实现方案.md` | 更正「Teleport」为互斥挂载 |
| `docs/requirements/features/image-consume/handoff.md` | 记录本缺陷 |

**明确不改：** 需求范围、IPC、后端、看图库选型。

## 回归

见 `tests.md`。
