# 任务 · photo-timeline-map

## 1. 对齐

- [x] 1.1 已读基线、需求、设计、实现方案与本 change
- [x] 1.2 开放问题已关闭（GPS 回填/筛选/入口并存）
- [x] 1.3 实现不超出实现方案文件清单

## 2. 数据与算法

- [x] 2.1 迁移 0017 + ORM/领域字段
- [x] 2.2 EXIF GPS 解析 + 导入写入
- [x] 2.3 GPS 纯函数单测

## 3. 时间线与回填

- [x] 3.1 列表过滤（takenDate/untimed/timelineVisible）
- [x] 3.2 时间线聚合（天/未知/总数/封面）
- [x] 3.3 回填用例与端点
- [x] 3.4 PATCH timelineVisible
- [x] 3.5 后端单测

## 4. 前端

- [x] 4.1 领域类型/HTTP/过滤参数
- [x] 4.2 照片页（时间线/网格）
- [x] 4.3 时间线组件（筛选/未知组/回填）
- [x] 4.4 日网格路由
- [x] 4.5 信息栏「计入时间线」

## 5. 契约与文档

- [x] 5.1 无既有 API 破坏；新增过滤/端点已记录
- [x] 5.2 两处 handoff 更新

## 6. 验收

- [x] 6.1 后端 188 passed；前端 typecheck/lint/build
- [x] 6.2 CDP 实测时间线/日网格/开关/回填
- [x] 6.3 `pnpm release:win` 重打包

## 7. v2 · Justified 照片流（2026-10-18）

- [x] 7.1 时间线接口返回每日照片瓦片（宽高/缩略图）
- [x] 7.2 后端分组与瓦片单测
- [x] 7.3 `justified-layout` + 粘性年月 + Justified 行/日段
- [x] 7.4 单击选中/双击查看器/查看当天/未知组
- [x] 7.5 typecheck/lint/build + CDP 布局验证

## 8. v3 · 时间线纳入视频（2026-10-18）

- [x] 8.1 video creation_time 解析 + 内嵌 ffprobe + `FFPROBE_BIN`
- [x] 8.2 时间线 media=image+video；瓦片 kind/duration
- [x] 8.3 日网格 `timelineMedia`；照片/视频混排
- [x] 8.4 「照片」改名「时间线」；视频时长/双击播放；信息栏计入开关
- [x] 8.5 回填扩到 video（只补时间）；后端 188 测试；CDP 验证
