# 设计 · photo-timeline-map

> L3 HOW；L2 见 `docs/requirements/features/photo-timeline-map/设计.md`。
> 与 `docs/requirements/features/photo-timeline-map/实现方案.md` 同一套文件清单。

## 上下文

- 现有：图片网格/分类/标签/合集；`files.exif_taken_at` 已存在；无 GPS/无时间线
- 基线：前端四层、后端 api/application/infrastructure；SQLite 迁移按 `NNNN_*.sql`
- 本刀地图 UI OUT；GPS 仅落库

## 与现有架构对齐

- 后端：新增 `photos` API 薄路由 + application 用例 + repository 聚合，沿用 `get_repos`
- 前端：新增 `Photos`/`PhotoDay` 视图与 `PhotoTimeline` 组件；日网格复用 `ResourceBrowser`
- **不**新开分层/数据库；不引入地图库

## 目标 / 非目标

**目标：** 时间线可用、可见性可控、旧图可回填、GPS 落库

**非目标：** 地图渲染/瓦片、反向地理编码、自动行程、视频 GPS、手动地图选点

## 方案

### 模块与文件

见 `实现方案.md` 文件清单（后端 13 项、前端 12 项）。

### 组合根

- 组合于：`views/Photos/index.vue`（时间线/网格切换）、`views/PhotoDay/index.vue`（日网格）
- 切片：算法（GPS 解析）/ 功能（时间线聚合、回填、PATCH）/ UI（时间线、日视图、信息栏开关）
- 最后一步：照片页接到路由与信息栏，主路径可验收

### 数据流

1. 导入 → `probe_image` → `files` 写 `exif_taken_at/exif_lat/lng`
2. 时间线 → repository 按 `substr(exif_taken_at,1,10)` 聚合；可见性三态；合集成员不排除
3. 某天 → `/library/resources?takenDate=…&timelineVisible=true`（`includeCollected=true`）
4. 开关 → PATCH `timelineVisible` → `resources.timeline_visible`
5. 回填 → `to_thread` 读 EXIF → 写 `files`；不改可见性

### 决策

| 决策 | 选择 | 为何不选备选 |
|------|------|----------------|
| 可见性 | NULL/1/0 三态 | 布尔无法区分自动与手动，回填会覆盖用户选择 |
| 时间线数据 | 后端按天聚合 | 前端分组受分页限制，无法得到全量计数 |
| 日视图 | 复用 ResourceBrowser + 过滤 props | 避免复制卡片/查看器/信息栏 |
| 回填 | 同步 + `to_thread` + spinner | 225 张量级；后台任务下刀 |
| GPS | 本刀落库 | 地图刀少扫一遍原图 |

## 风险

| 风险 | 表现 | 缓解 |
|------|------|------|
| EXIF 缺失/格式异常 | 未知时间组 | 回填统计失败数；不伪造 |
| 回填阻塞 | 大库超时 | v1 量级；后续后台任务 |
| 三态语义 | 用户不理解自动/手动 | 信息栏文案；后续加「恢复自动」 |
| 迁移 | 旧库时间线空白 | 回填按钮 + 空态说明 |

## 迁移与回滚

- 迁移 0017：加列（nullable），旧数据默认自动
- 回滚：停止使用新页面即可；列可保留

## 注释与可维护性

- 三态规则、时间线聚合过滤、回填「不清空/不覆盖」需中文注释


## v2 · Justified 照片流（2026-10-18 追加）

- 视觉：粘性年/月 + 日段 + 逐行 Justified；不做 Apple 年/月三层
- 接口：`GET /library/photos/timeline` 每日增加 `photos: PhotoTile[]`（id/宽高/缩略图/拍摄时间）；保留计数
- 前端：`justified-layout`（ISC）算行，现有 TanStack/选中/查看器复用；单击选中、双击打开
- 文件：`components/PhotoTimeline` 重写 + `PhotoRow.vue`；`domain/photo.ts`/schemas/repositories/photos service 扩展
- 规模：v1 全量返回（225 张），>2000 再按月懒加载
- 验证：T8/T9（瓦片字段 + Justified 布局/CDP）

## v3 · 时间线纳入视频（2026-10-18 追加）

- 类型：`image + video`；入口改名「时间线」；日志/瓦片带 `kind`、`duration`
- 视频时间：ffprobe `format.tags.creation_time` → 本地时间 → `files.exif_taken_at`
- 内嵌 ffprobe：`@ffprobe-installer/win32-x64` 复制到 `resources/ffprobe`；主进程注入 `FFPROBE_BIN`
- 日网格：`timelineMedia` 过滤；照片/视频混排
- 回填：image+video；视频只补时间
- 验证：T10/T11（后端 188 + CDP 视频瓦片/播放/混排）
