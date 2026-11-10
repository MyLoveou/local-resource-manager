# 跨会话续作 · photo-timeline-map（能力目录）

> 与 `openspec/changes/photo-timeline-map/handoff.md` 对齐。

## 状态

- 阶段：`待打包验收`
- 最后更新：2026-10-18 · 时间线（v1）实现完成；地图下一刀

## 已完成

- v1 时间线：照片页、天分组、未知时间、分类/标签筛选、日网格
- 每图「计入时间线」三态（默认按 EXIF 自动）
- 旧图回填：拍摄时间 + GPS；不改原图、不覆盖手动可见性
- 导入解析 GPS；后端 186 测试、前端三查、CDP 验证

## 下一步

1. `pnpm release:win` 重打安装包
2. 用户手验
3. 地图刀：Leaflet + MarkerCluster + LayersControl（OSM/Esri）、GCJ-02、无 GPS 提示

## 阻塞

- 待确认：安装包手验结果
