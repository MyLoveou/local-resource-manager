# 设计 · fix-image-consume-ui

纯修复，不改契约。

- InfoPanel：**不要** Teleport。壳 `v-if="!viewerOpen"`，覆盖层左侧 `v-if="visible"`，同一时刻只有一份。
- Viewer.js：只在封装内 `new Viewer` 一次；源 img 透明不占交互；`fullscreen: false`；画布 CSS 限制在右侧 host。
