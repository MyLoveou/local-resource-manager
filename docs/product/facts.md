# 项目事实基线

> 只写**已确认**的实现与方向。推测标「未确认」。  
> 约束/禁止项见 [浓缩基线](baseline.md) / [openspec/baseline.md](../../openspec/baseline.md)。  
> 历次拍板见 [decisions.md](decisions.md)。

**最后核对**：2026-10-25 · v0.2.4；资源库工作区、照片时间线、合集、角色/扮演者、地图、AI 图片检索与文案、备份恢复、Windows 生产包已实现，并已用 Electron 全量手验通过（D-20261025-01）；图片库阶段收口，进入视频阶段；下载方向拍板 D-20261007-01（不自建，委托第三方下载器）。

---

## 一、项目实现（现状）

### 做什么（仓库里真实存在）

- 产品一句话：单机桌面工作台的**第一形态**是本地媒体库（图片/视频）；后续在同一壳里扩展工作上下文、模型/游戏等类型，以及设计系统与 AI 资产。
- 已交付（代码在库内，2026-10-25 完成 Electron 全量手验）：
  - 启动 Electron 窗口；主进程拉起本机 FastAPI；健康检查通过后才开窗。首页按类型计数，并列出进行中工作与最近消费。
  - 九种类型都能导入并最低打开：图片查看器（含跨页）、视频与番剧/AV 选集播放、音频 Howler、模型 gltf 预览、小说/漫画/游戏系统打开。游戏默认只登记路径。
  - 虚拟网格 + 触底分页；信息栏可保存评分/分类/标签/待办/简介、弹窗编辑、换封面。回收站软删、恢复、彻底删除库内包、批量模式（T10–T16 已手验）。全类型「打开所在位置」。
  - 顶栏导入：选类型与文件/文件夹，复制进库并 sha256 去重。新导入写 `thumbs/grid.webp`；旧资源仍可能拉原图。封面：手选锁定、旁海报、抽帧、音频内嵌、exe/lnk、EPUB/PDF/cbz。图片 EXIF 拍摄时间可手改；机身/镜头/ISO/光圈/快门只读展示（Pillow，不写回文件）。拍摄时间旧库不自动回填（有独立回填接口）。
  - 番剧/AV：作品级 Resource + 季集树（A-min）。整理、字幕组、女优仍 OUT。
  - 搜排：标题/作者/描述/分类/标签/文件名 LIKE；顶栏跨类型；标签多选 AND。壳层主题：内置 + 一份本机 css，顶栏批量条。
  - 刮削：`/scrape/jobs` 搜索与确认回填。视频 TMDB + B 站公开稿件（BV、链接或名称）。番剧 Bangumi + 蜜柑发现。图片填公网页面链接，读 Open Graph（D-20260923-05）。确认队列按字段勾选。
  - 下载：**已移除**（D-20261007-01）：不自建下载，统一委托第三方成熟下载器；原 HTTP 直链/磁力第一刀代码与测试已删除。下载产物按下载器自身目录结构存放，本应用不管理；入库只靠监视下载目录增量导入。
  - 设置：刮削凭证、系统路径与备份、按类型的消费渠道（内嵌 / 系统 / 自定义命令；工作目录默认只留在工作台）。自定义命令由主进程拆词执行，`{path}` 单独成参。
  - 工作目录：顶栏添加本地文件夹（只登记路径，不复制不扫描）。信息栏待办与备注。再次点击不打开文件夹。回收站里的同一路径再次添加会恢复。
  - Notify：`notify` Facade；后端起不来或中途退出时右下角 Push。视图内旧提示已全部迁完（2026-09-27，全库无 `useMessage`）。
  - 导入进度：按阶段展示（校验 → 复制 → 探测 → 封面 → 缩略图 → 入队刮削），前端 ImportWizard 逐步显示。
- **尚未实现**（需求或路线有，工作区没有可用入口）：
  - 改库根路径、扫描根、适配器表管理、播放器渠道。
  - 右键菜单、紧凑列表、FTS5、按标签独立浏览、词表统计与删除。
  - AV 刮削、SearXNG、Pixiv 登录、适配器配置表、远程索引。
  - 番剧/AV 第二刀（规范重命名、增删集、字幕组、女优、集封面双列表）。
  - rqbit / yt-dlp。合集、画廊沉浸、小说与漫画内置阅读器。
  - 设计系统、提示词、Skill、导出、加密。
  - 常驻文件监视源目录**已实现**（`watch-source-dirs`，2026-10-07）：按类型配置监视目录、事件按类型派发、启动/设置后补扫、自动导入（sha256 去重、攒批并发、**anime/av 目录级增量挂集**）、前端轮询软刷新；待 Electron 手验。
  - **批量打标 + 合集导出已实现**（`batch-tag-export`，2026-10-07）：批量端点扩展 `add_tags`（只加不删、幂等、多标签）；顶栏批量条「打标」输入框；合集成员页「导出」按钮，按成员顺序复制主文件到所选目录，命名 `{序号3位}_{安全标题}{后缀}`，缺失文件跳过计数；命名规则为纯函数算法切片；后端 14 个新单测，待 Electron 手验。漫展返图工作流：**按 coser 建分类**（分类词表既有能力，零开发）。
  - **合集交互收口**（2026-10-18）：加入合集改为「勾选暂存 + 取消/确定」；主列表默认隐藏合集成员（类型页/全库混排/首页 by_type），「显示合集内资源」为全局持久化开关（合集列表页头部/类型页工具栏），搜索与回收站不受影响；合集详情支持按分类/标签（AND）筛选成员；合集详情可删除（只删关系、资源保留）；**批量选中可加入合集**（弹窗选已有/新建，返回 added/skipped/missing，超过 200 项前端分批；只加关系）；普通浏览恢复选中描边、合集卡不可选中；后端 +4 单测（181 passed）。
  - **照片时间线已实现**（`photo-timeline-map`，2026-10-18）：独立「时间线」页（时间线/网格）；时间线为 **Justified 照片流**（粘性年/月 + 日段 + 逐行等高照片，`justified-layout`）；图片类型页/时间线网格同样 Justified（列表附 primary 宽高）；**包含本机拍摄的 video**（ffprobe `creation_time`，内嵌 ffprobe，时长角标，双击播放）；按拍摄日分组 + 未知时间组；每图「计入时间线」三态（默认按 EXIF/creation_time 自动）；年/月/分类/标签筛选；旧图回填（拍摄时间 + GPS，不改原图、不覆盖手动可见性）；导入解析 GPS；导入向导可选「计入时间线」；取消计入后时间线保留滚动位置；图片页批量选择后可继续加载（底部兜底按钮 + nearEnd 重置）；**地图视图已实现**（Leaflet + MarkerCluster + LayersControl，GPS 点聚类、点击打开资源）；后端 201 测试通过。
  - **资源库工作区已实现**（`library-workspace`，2026-10-19）：资源库统一路由 `/library/:type`，类型 tabs + 可折叠分类树 + 网格（资源库地图占位已移除；地图为独立顶级入口）；分类改为**每类型独立树**（`0018` 迁移、多对多 `resource_categories`、最多 4 层、单节点筛选含后代、`待整理分类` 系统根、多分类赋值）；保存时间线 `saved_views`（多分类并集、无成员表、默认排除未知时间）；首页 `/library/home` 聚合最近添加/合集/时间线；首页概览按类型展示最近图片/视频叠图 + 数量，最近消费展示封面/类型/动作/时长/时间；合集 D 叠图卡（`previewThumbnails≤3`）；批量 Ctrl/Shift/Esc；旧类型路由与 `/photos` 重定向；迁移在真实库副本对账通过；198 测试，打包已重出（0.1.2）。数据变更统一走按 scope 的 `library.invalidate`：批量分类后资源列表/分类树/首页自动失效重取，分类树 HTTP 层不再保留第二份缓存。
  - **时间线中心已实现**（`timeline-hub`，2026-10-19）：一级「时间线」入口；保存时间线支持 scope（图片/视频/全部媒体）、图片/视频分类分别包含/排除、标签/日期/未知时间；`/timelines/all` 内置全部媒体；详情竖向 Justified；编辑/删除规则；`/photos` 重定向；首页时间线卡片跳详情；无成员表。
  - **时间线备注与地点已实现**（`timeline-annotations`，2026-10-20）：`0020` 新增 `timeline_notes`；日期备注为全局单条，保存时间线备注为单条；标题/正文/地点名；`/library/timeline-notes` CRUD；时间线日段显示/编辑日期备注，时间线详情显示/编辑备注；地点名不写 EXIF，无反向地理编码；地图使用照片 GPS。
  - **角色 + 作品维度第一刀已实现**（`photo-management-next` R3，2026-10-22）：`0023` 新增 works/characters/character_aliases/resource_characters；角色 CRUD（名称、别名、作品、简介、封面默认取最近关联资源）、资源多角色、批量设置角色、角色合并；`/characters` 聚合图片/视频、时间线和所在合集；类型页/时间线/地图支持按角色筛选；扮演者暂用标签过渡，不建一等实体。
  - **扮演者实体已实现**（`person-dimension`，2026-10-22）：`0024` 新增 persons/person_aliases/resource_persons；扮演者 CRUD、别名、资源多对多、批量设置、合并；`/persons` 人物页聚合图片/视频并显示相关角色；类型页/时间线/地图支持按扮演者筛选；角色↔扮演者通过共同关联资源派生。
  - **地图/GPS 已实现**（`photo-timeline-map` 后续，2026-10-20；2026-10-21 切换引擎并独立入口）：顶级「地图」`/maps` 与 `/maps/:id` 使用 Leaflet + MarkerCluster，内置 LayersControl 切换 OSM/Esri 浅色/深色底图，按 GPS 聚类；地图规则复用 `saved_views` 的 `kind='map'`，可新建/编辑/删除；`resources.map_visible` 独立控制加入地图（NULL=有 GPS 自动纳入，1=加入，0=排除），导入向导与信息栏可设置；图片/视频均解析 GPS（视频读取 ffprobe location/QuickTime ISO6709），地图查询使用 GPS + `map_visible`，不依赖时间线可见性；聚合点取簇内首张缩略图并叠加数量角标，单点使用缩略图圆形标记；点击聚合点查看该位置缩略图，点击缩略图打开资源，打开资源后保留聚合面板；右侧「城市 / 地点」面板使用本地城市库做最近城市分组（不上传坐标），点击城市聚焦；`PhotoTile` 返回 `lat/lng`；不引入反向地理编码或轨迹；OSM/Esri 在线瓦片会暴露当前地图视口/瓦片请求，不上传照片或精确坐标字段。
  - **应用内更新已实现**（`app-update`，2026-10-18）：electron-updater + GitHub Releases；启动/设置页检查、更新公告、下载、重启安装；版本 0.1.1 为首个 updater 版本（需手动装一次），之后 `v*` tag 由 CI 发布 Release；**v0.1.2 Release 已于 2026-10-19 发布成功（5 个资产）**；更新说明清洗、下载速度/剩余时间、手动下载兜底已在工作区实现，**不在 0.1.2 包内，待下个版本发布**；仍未签名，自动更新慢受 GitHub 网络影响；完整更新链路待安装版手验。
  - **分区可见性已实现**（`section-visibility`，2026-10-07）：代码配置 `HIDDEN_SECTIONS`（`domain/visibility.ts`，默认 `/av /anime /novel /comic /game /model`）统一控制菜单、路由直达（重定向首页）、导入向导类型、首页概览卡；`/` 不可隐藏；搜索与合集混排不过滤；不改后端/DB，清空配置即恢复；`/anime` 于安装包反馈后追加；待 Electron 手验。
  - **Windows 生产包与校验流水线已实现**（`production-packaging`，2026-10-07）：`pnpm release:win` 一条命令产出 NSIS 安装包 + 绿色版 zip + SHA256；后端 PyInstaller onedir 随包（无需用户 Python）；生产态数据/日志落 `%APPDATA%/local-resource-manager`；verify 强制冻结后端 `/health` 冒烟；GitHub Actions `release-windows.yml` 复用同一入口；应用图标已设计（`build/icon.ico`，`build/generate-icon.py` 可复现）；安装目录默认 `%LOCALAPPDATA%\Programs\资源管理器`（可执行名保持 ASCII）；安装器提供「创建桌面快捷方式」复选框（默认勾选，静默安装仍创建）；安装与 dev 手工回归待跑。

### 怎么做的（路径级）

| 层 | 技术 | 目录 / 入口 | 备注 |
|----|------|-------------|------|
| 桌面壳 | Electron 44 + TS | `apps/desktop/src/main` | `spawn` uvicorn；动态端口；`additionalArguments` 注入 URL/token |
| UI | Vue 3 + Vite + naive-ui + Pinia + vue-router | `apps/desktop/src/renderer/src` | 四层：`ui` / `application` / `domain` / `infrastructure` |
| 后端 | FastAPI + uvicorn | `apps/backend/app/main.py` | **一个进程**，`include_router`：`/library` `/scrape` `/ai` `/settings` |
| 数据 | SQLite + SQLAlchemy async + aiosqlite | `apps/backend/app/shared/db` | WAL；启动 `ensure_db`；**新库不再 demo seed** |
| 鉴权 | 主进程生成 token，axios Bearer | `apps/backend/app/shared/middleware/auth.py` | 后端校验 Bearer；媒体 `/content` 使用短期 path-bound 签名 URL |

- 主数据流：渲染进程 axios → `http://127.0.0.1:<port>/library/...` → `LibraryQueryService` → `ResourceRepository` → SQLite。
- 关键模块：
  - `apps/desktop/src/main/infrastructure/services/` — 端口、配置、spawn、停进程
  - `apps/backend/app/library/api/` — health / overview / resources / imports
  - `apps/desktop/src/renderer/src/hooks/useResourcePage.ts` — 分页列表状态
  - `apps/desktop/src/renderer/src/application/stores/selection.ts` — 当前选中 id
  - `apps/backend/app/scrape/` — 刮削任务与渠道；确认回填走 library 封面与仓储
  - `apps/backend/app/ai/` — CLIP/YOLO 索引、VLM/WD14 文案、检索与相似图
- 构建 / 启动：见浓缩基线。

### 实现边界（已确认）

- 本仓负责：桌面壳、本机后端、SQLite 资源库、后续自建抓取与内置下载编排。
- 本仓不负责：移动端、多用户账号、在线流媒体服务、资源分享。
- 已知债（有路径）：
  - `useResourceHandle.refreshResourceList` 不更新 `useResourcePage.items` — 已由按 scope 的 `library.invalidate` 让资源列表 reset（待手工验网格）。
  - README 仍写「无业务代码 / mount 双应用」，与现状不符。
  - 路线图 `docs/design/00-路线图与里程碑.md` 进度表已按 2026-09-23 核对：MS2 主路径完成；MS3 与 MS7 仅第一刀；设置未做。
  - 导入 `phase=probe`：Pillow 宽高与 **EXIF 拍摄时间**；ffprobe 视频字段。图片拍摄可 PATCH 手改。缺列面板「—」。开发阶段以清库重导代替回填。

---

## 二、项目方向（已确认 · 2026-09-12 叠加 L1）

### 要成为什么

- **近端（A · 媒体库）**：每种库类型先具备 **导入 + 最低消费**。类型含图片、视频、番剧、AV、音频、小说、游戏、模型、**漫画**。漫画为本刀独立 type（D-20260917-02）。小说/漫画内置阅读器另立项。音频/模型用成熟库内置播/预览。游戏默认扫描登记源路径（D-20260917-03）。合集仍后置。抓取与下载只提前了第一刀，不等于原文 M3/M5 做完。
- **中段（B · 不完整工作台）**：在 A 可用之后，加工作目录 + 消费渠道（按类型打开），**不是** WCH 草案的完整形态。
- **远期可扩展类型**：模型文件（含预览）、游戏（单机 / Gal / 黄油等）。菜单占位可早出现，能力按类型插件化加。
- **功能模块骨架**（规划用，未逐项定稿）：见 [module-map.md](module-map.md)。
- **远期资产域**（不挡 A）：设计系统管理、AI 提示词、Skill、导出。
- 明确不做（方向级）：在线播放平台、移动端、多用户、对外社交分享；下载不含 ED2K/WebDAV。

### 原则（已拍板）

- 产品：单机本地优先；先闭环媒体库，再长工作台；类型与资产域可插拔，避免为远期功能改死核心模型。
- 导入：用户选择文件或目录**一次**；媒体默认**复制**进库并写库、算元数据；**游戏默认只登记路径**（可选手动复制）。**新导入 owned 包内生成网格缩略图**（`thumbs/grid.webp`）；前端只选路径。**允许对用户显式添加的源目录做常驻监视**（D-20260927-01，事件增量），**不把源目录登记为可再扫的根**。
- 分类与标签为**独立词表**；资源面板可新建词条并点保存挂上。词条统计/删除管理的需求已于 2026-09-27 定稿（`D-20260927-02`），**尚未实现**。
- **资源组织后续（2026-10-19）**：角色/人脸（R3/R4）、反向地理编码/轨迹、时间线成员表仍 OUT；当前已落地「资源为底层 + 每类型分类树 + 资源库视图 + 保存筛选时间线 + GPS 地图 + 日期/时间线备注」。
- 三栏信息栏默认不折叠（L1，未改口）。
- 技术：Electron+Vue；单一 FastAPI 进程；SQLite。抓取直连官方 API 与页面 Open Graph（SearXNG 未做，D-20260923-05）。下载：**不自建，委托第三方成熟下载器**（D-20261007-01）；下载产物经监视目录入库。
- 契约：DB snake_case ↔ API JSON camelCase。JSON 业务响应统一信封 `{ code, status, message, data }`（成功 `code=0`）；文件流与 OpenAPI 不包；前端 axios 解开 `data`。

### 近期顺序

1. **A-min（所有库最低消费）**：各类型导入策略 + 列表/详情/回收站 + 该类型基本打开方式（图看、视频播、番剧/AV 选集播、音频播、小说读、游戏启动、模型预览或系统打开）。
2. 收口已有图/视频闭环缺口（列表与删除一致、播放稳定）。
3. **A-plus**：搜排 LIKE、抓取（视频/番剧/图片页面链接）已手验；下载已改道（D-20261007-01 不自建）。**已实现并手验**：合集（`library-collections`：跨类型多对多、手动排序、全库视图混排合集卡、监视视频目录自动归集、bilidown EP 前缀）、监视目录自动导入（`watch-source-dirs`）。**需求已定稿待实现**：词表治理（`D-20260927-02`）、主题令牌（`D-20260927-04` → `features/theme-tokens/`）。仍后置：系列整理与档案、画廊沉浸、AV 刮削、SearXNG、远程索引（D-20260919-09）、设置完整。
4. **B 不完整工作台**：需求已于 2026-09-27 定稿（`D-20260927-05`），主体已编码并手验，不再返工。
5. 设计系统、提示词、Skill、导出：远期资产域，单独立项。

与单功能稿冲突时：以本文**已确认**方向为准。WCH 已定稿（`D-20260927-05`）；高级能力不得插队挡住「某类型还不能打开」。

---

## 未确认

- 导出的第一刀导出什么（资源库备份 / 设计系统包 / 提示词与 Skill 包）。
- 设计系统、提示词、Skill 是独立顶栏域，还是「资源类型」的一种。
- `theme-tokens` 的令牌覆盖面（Q1–Q4，见 `docs/requirements/features/theme-tokens/需求.md`）。
- `quality-and-deploy` 的 S1（设置页）/ S2（下载与刮削弹层）具体现象：未给出前保持 OUT。
- 新能力是否一律 `features/<id>/需求.md`。三个早期 change 已归档（D-20260923-01）。
- metadata-panel 的 T7–T12 已按用户授权归档（D-20260923-03），本会话未重跑 Electron。
- 参考产品全功能对照与路线见 [reference-landscape.md](reference-landscape.md)；A-min 已拍板（D-20260917-01）。库类型打开方式见 D-20260917-02。
- 后续还能加哪些能力、建议顺序见 [后续能力规划.md](后续能力规划.md)（草案，未拍板）。

改实现或改方向：先记 `decisions.md`，再改本文对应句。
