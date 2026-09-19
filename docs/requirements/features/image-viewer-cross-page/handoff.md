# 跨会话续作 · image-viewer-cross-page

## 状态

- 阶段：已落地 D-20260919-08，待 Electron 手验 T1–T6
- 最后更新：2026-09-19

## 已完成

- `需求.md`、`设计.md`、`实现方案.md`
- `bindPager` + 末张 `await loadMore` + 距末 2 张预拉 + bump 关查看器

## 下一步

Electron：图片页打开第 80 张点下一张 → 第 81 张；第一张上一张禁用；搜排后顺序与网格一致；没有更多则下一张禁用；加载失败不关查看器；导入 bump 关闭查看器。

## 关键路径

`imageViewer.ts`、`ResourceBrowser`、`useResourcePage` inflight。
