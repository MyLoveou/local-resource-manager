# 测试 · photo-timeline-map

## 映射

| Spec 场景 | 切片 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|------|---------|------|------------|------|
| 时间线主路径 | 功能+UI | T1 | 单测+CDP | 后端分组测试；照片页时间线 | 天分组/总数正确 |
| 点日进网格 | UI | T2 | CDP | 点第一天 | 路由 `/photos/day/…`，网格可选中 |
| 未知时间/筛选 | 功能 | T3 | 单测 | 无 takenAt + includeAll | 未知组计数正确；筛选一致 |
| 可见性自动 | 功能 | T4 | 单测 | takenAt + NULL | 默认计入 |
| 手动覆盖 | 功能 | T5 | 单测+CDP | PATCH false；时间线总数 | -1；回填不覆盖 |
| 回填 | 功能 | T6 | 单测+CDP | `POST /photos/backfill` | 补时间/GPS，统计返回 |
| GPS 解析 | 算法 | T7 | 单测 | 度分秒/南纬/西经 | 十进制度正确 |
| 回归 | — | R1 | 构建 | typecheck/lint/pytest/build | 全绿 |

## 命令

```powershell
pnpm --filter desktop typecheck
pnpm --filter desktop lint
pnpm --filter desktop build
apps/backend/.venv/Scripts/python -m pytest -q apps/backend/tests
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1 | PASS | 时间线 days=1、total=225（测试库副本） | 2026-10-18 |
| T2 | PASS | CDP：`#/photos/day/2026-10-17`，网格可选中 | 2026-10-18 |
| T3 | PASS | 单测 unknown_count=1；includeAll 切换 | 2026-10-18 |
| T4 | PASS | 单测：有 takenAt + NULL → 计入 | 2026-10-18 |
| T5 | PASS | CDP：取消后 225→224；DB timeline_visible=0 | 2026-10-18 |
| T6 | PASS | CDP 回填完成；DB GPS 225 条；taken 236 | 2026-10-18 |
| T7 | PASS | `_gps_coord` 单测（N/S/W/非法） | 2026-10-18 |
| T8 | PASS | 时间线响应含每日瓦片（缩略图/宽高）；单测断言 | 2026-10-18 |
| T9 | PASS | CDP：224 瓦片、月/日标题、首图 163×217、单击选中、双击查看器 | 2026-10-18 |
| T10 | PASS | 后端视频瓦片 kind/duration/taken_at；188 passed | 2026-10-18 |
| T11 | PASS | CDP：225 瓦片、视频时长 0:02、双击播放、日网格混排、信息栏开关 | 2026-10-18 |
| T12 | PASS | CDP：图片页 Justified 80 瓦片、选中；时间线取消计入后滚动 600 保持、总数 -1 | 2026-10-18 |
| T13 | PASS | 导入 timeline_visible=false 单测；合集删除 CDP；全局开关显示 | 2026-10-18 |
| R1 | PASS | 后端 189 passed；前端三查全绿 | 2026-10-18 |

## 未覆盖

- 地图 UI（下一刀）
- 回填大库性能（v1 同步）
