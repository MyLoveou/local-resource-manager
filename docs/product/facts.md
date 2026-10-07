# 项目事实基线

> 只写**已确认**的实现与方向。推测标「未确认」。  
> 约束/禁止项见 [浓缩基线](baseline.md) / [openspec/baseline.md](../../openspec/baseline.md)。  
> 历次拍板见 [decisions.md](decisions.md)。

**最后核对**：2026-10-07 · 监视目录（watch-source-dirs）全链路已实现待手验；下载方向拍板 D-20261007-01（不自建，委托第三方下载器）。

---

## 一、项目实现（现状）

### 做什么（仓库里真实存在）

- 产品一句话：单机桌面工作台的**第一形态**是本地媒体库（图片/视频）；后续在同一壳里扩展工作上下文、模型/游戏等类型，以及设计系统与 AI 资产。
- 已交付（代码在库内。写「待手验」的还没在本环境用 Electron 点完）：
  - 启动 Electron 窗口；主进程拉起本机 FastAPI；健康检查通过后才开窗。首页按类型计数，并列出进行中工作与最近消费（待手验）。
  - 九种类型都能导入并最低打开：图片查看器（含跨页）、视频与番剧/AV 选集播放、音频 Howler、模型 gltf 预览、小说/漫画/游戏系统打开。游戏默认只登记路径。
  - 虚拟网格 + 触底分页；信息栏可保存评分/分类/标签/待办/简介、弹窗编辑、换封面。回收站软删、恢复、彻底删除库内包、批量模式（待手验 T10–T16）。全类型「打开所在位置」。
  - 顶栏导入：选类型与文件/文件夹，复制进库并 sha256 去重。新导入写 `thumbs/grid.webp`；旧资源仍可能拉原图。封面：手选锁定、旁海报、抽帧、音频内嵌、exe/lnk、EPUB/PDF/cbz。图片 EXIF 拍摄时间可手改。旧库不回填。
  - 番剧/AV：作品级 Resource + 季集树（A-min）。整理、字幕组、女优仍 OUT。
  - 搜排：标题/作者/描述/分类/标签/文件名 LIKE；顶栏跨类型；标签多选 AND（待手验）。壳层主题：内置 + 一份本机 css，顶栏批量条（待手验）。
  - 刮削：`/scrape/jobs` 搜索与确认回填。视频 TMDB + B 站公开稿件（BV、链接或名称）。番剧 Bangumi + 蜜柑发现。图片填公网页面链接，读 Open Graph（D-20260923-05）。确认队列按字段勾选。待手验。
  - 下载：**已移除**（D-20261007-01）：不自建下载，统一委托第三方成熟下载器；原 HTTP 直链/磁力第一刀代码与测试已删除。下载产物按下载器自身目录结构存放，本应用不管理；入库只靠监视下载目录增量导入。
  - 设置：刮削凭证、系统路径与备份、按类型的消费渠道（内嵌 / 系统 / 自定义命令；工作目录默认只留在工作台）。自定义命令由主进程拆词执行，`{path}` 单独成参。待手验。
  - 工作目录：顶栏添加本地文件夹（只登记路径，不复制不扫描）。信息栏待办与备注。再次点击不打开文件夹。回收站里的同一路径再次添加会恢复。待手验。
  - Notify：`notify` Facade；后端起不来或中途退出时右下角 Push。视图内旧提示已全部迁完（2026-09-27，全库无 `useMessage`）。
  - 导入进度：按阶段展示（校验 → 复制 → 探测 → 封面 → 缩略图 → 入队刮削），前端 ImportWizard 逐步显示。
- **尚未实现**（需求或路线有，工作区没有可用入口）：
  - 改库根路径、扫描根、适配器表管理、播放器渠道。
  - 右键菜单、紧凑列表、FTS5、按标签独立浏览、词表统计与删除。
  - AV 刮削、SearXNG、以图搜图、Pixiv 登录、适配器配置表、远程索引。
  - 番剧/AV 第二刀（规范重命名、增删集、字幕组、女优、集封面双列表）。
  - rqbit / yt-dlp。合集、画廊沉浸、小说与漫画内置阅读器。
  - 设计系统、提示词、Skill、导出、加密。
  - 常驻文件监视源目录**已实现**（`watch-source-dirs`，2026-10-07）：按类型配置监视目录、事件按类型派发、启动/设置后补扫、自动导入（sha256 去重、攒批并发）、前端轮询软刷新；待 Electron 手验。

### 怎么做的（路径级）

| 层 | 技术 | 目录 / 入口 | 备注 |
|----|------|-------------|------|
| 桌面壳 | Electron 44 + TS | `apps/desktop/src/main` | `spawn` uvicorn；动态端口；`additionalArguments` 注入 URL/token |
| UI | Vue 3 + Vite + naive-ui + Pinia + vue-router | `apps/desktop/src/renderer/src` | 四层：`ui` / `application` / `domain` / `infrastructure` |
| 后端 | FastAPI + uvicorn | `apps/backend/app/main.py` | **一个进程**，`include_router`：`/library` `/scrape` `/download` `/settings` |
| 数据 | SQLite + SQLAlchemy async + aiosqlite | `apps/backend/app/shared/db` | WAL；启动 `ensure_db`；**新库不再 demo seed** |
| 鉴权 | 主进程生成 token，axios Bearer | 后端**未校验** | 与需求「token 鉴权」不一致 |

- 主数据流：渲染进程 axios → `http://127.0.0.1:<port>/library/...` → `LibraryQueryService` → `ResourceRepository` → SQLite。
- 关键模块：
  - `apps/desktop/src/main/infrastructure/services/` — 端口、配置、spawn、停进程
  - `apps/backend/app/library/api/` — health / overview / resources / imports
  - `apps/desktop/src/renderer/src/hooks/useResourcePage.ts` — 分页列表状态
  - `apps/desktop/src/renderer/src/application/stores/selection.ts` — 当前选中 id
  - `apps/backend/app/scrape/` — 刮削任务与渠道；确认回填走 library 封面与仓储
  - `apps/backend/app/download/` — HTTP 直链任务；桌面入口 `DownloadDrawer`
- 构建 / 启动：见浓缩基线。

### 实现边界（已确认）

- 本仓负责：桌面壳、本机后端、SQLite 资源库、后续自建抓取与内置下载编排。
- 本仓不负责：移动端、多用户账号、在线流媒体服务、资源分享。
- 已知债（有路径）：
  - `useResourceHandle.refreshResourceList` 不更新 `useResourcePage.items` — 已由 `library-trash` 用 `library.bump(null)` 让列表 reset（待手工验网格）。
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
- 三栏信息栏默认不折叠（L1，未改口）。
- 技术：Electron+Vue；单一 FastAPI 进程；SQLite。抓取直连官方 API 与页面 Open Graph（SearXNG 未做，D-20260923-05）。下载：**不自建，委托第三方成熟下载器**（D-20261007-01）；下载产物经监视目录入库。
- 契约：DB snake_case ↔ API JSON camelCase。JSON 业务响应统一信封 `{ code, status, message, data }`（成功 `code=0`）；文件流与 OpenAPI 不包；前端 axios 解开 `data`。

### 近期顺序

1. **A-min（所有库最低消费）**：各类型导入策略 + 列表/详情/回收站 + 该类型基本打开方式（图看、视频播、番剧/AV 选集播、音频播、小说读、游戏启动、模型预览或系统打开）。
2. 收口已有图/视频闭环缺口（列表与删除一致、播放稳定）。
3. **A-plus**：搜排 LIKE、抓取（视频/番剧/图片页面链接）、下载 HTTP 直链与磁力（aria2）已编码，待手验。**需求已定稿待实现**：词表治理（`D-20260927-02`）、合集（`D-20260927-03`）、主题令牌（`D-20260927-04` → `features/theme-tokens/`）。仍后置：系列整理与档案、画廊沉浸、AV 刮削、SearXNG、远程索引（D-20260919-09）、rqbit、设置完整。
4. **B 不完整工作台**：需求已于 2026-09-27 定稿（`D-20260927-05`），主体已编码待手验；只剩手验，不再返工。
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
