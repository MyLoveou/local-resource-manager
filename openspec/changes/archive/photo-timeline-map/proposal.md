# 提案 · photo-timeline-map

> 对照：`docs/requirements/features/photo-timeline-map/需求.md`（已定稿）
> v1 只做时间线；地图下一刀（MapLibre+OSM 已定）

## 为什么

- 用户有旅游/漫展照片；现有只有网格与排序，缺按拍摄时间组织的浏览方式
- 网图与自拍混在库里，需要决定哪些进入时间线/地图
- 旧图导入时未解析 EXIF，需要回填才能进入时间线；GPS 也从未落库

## 做什么

- 新增独立「照片」页：时间线 / 网格
- 时间线按拍摄日分组；未知时间单独分组；可切「显示全部照片」
- 每图「计入时间线」开关：默认按 EXIF 自动，可手动覆盖
- 时间线筛选：年/月、分类、标签（AND）；包含合集成员
- 旧图回填：重读 EXIF 写回拍摄时间 + GPS（不复制、不改原图、不覆盖手动可见性）
- 导入时解析 GPS 落库；地图 UI 不在本刀
- **v2（2026-10-18 追加）**：时间线从「按天小行列表」改为 **Justified 照片流**（粘性年/月 + 日段 + 逐行等高照片）；接口直接返回每日照片瓦片；使用 `justified-layout`
- **v3（2026-10-18 追加）**：时间线纳入本机拍摄视频（image+video）；ffprobe `creation_time`；内嵌 ffprobe；时长角标/双击播放；入口改名「时间线」
- **BREAKING**：无

## 范围

| | 内容 |
|--|------|
| IN | 时间线页/未知组/可见性三态/筛选/日网格/回填/GPS 落库；v2 Justified 照片流 + 瓦片接口 |
| OUT | 地图 UI、瓦片、反向地理编码、自动行程切分、视频 GPS |
| 假设 | 「照片」与「图片」入口 v1 并存（已确认） |

## 能力（Capabilities）

### 新增

- `photo-timeline`：按拍摄时间组织照片的时间线、可见性与回填

## 规范对齐

- 基线：单一 FastAPI 进程、SQLite、前端四层 → 遵守
- 动工门禁：L1/L2 已定稿
- 冲突：无

## 现状要点（有路径）

- `files.exif_taken_at` 已有；无 GPS
- `library/application/media_probe.py` — 图片探测入口
- `library/infrastructure/repositories.py` — 列表/计数过滤
- 前端 `ResourceBrowser`/`VirtualGrid`/`InfoPanel` 可复用
- `image-library-depth` N2/N6/N7 已列方向

## 影响

- 表：`resources.timeline_visible`、`files.exif_lat/lng`（迁移 0017）
- API：`/library/photos/*`；资源列表新增 3 个过滤参数；PATCH 新增字段
- 前端路由：`/photos`、`/photos/day/:date`
- 文档：需求/设计/实现方案、change、facts/decisions

## 验收意图（详情在 tests.md）

- 主路径：导入→时间线分组→点日→网格；开关改变可见性
- 边界：无拍摄时间进未知组；网图默认不进（无 EXIF）；合集成员仍计入
- 回填：旧图补时间/GPS；手动可见性不被覆盖
- 回归：现有图片网格/主列表/合集隐藏不受影响

## 开放问题

1. 无（回填 GPS/筛选/入口并存已确认）
