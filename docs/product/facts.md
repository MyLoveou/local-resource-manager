# 项目事实基线

> 只写**已确认**的实现与方向。推测标「未确认」。  
> 约束/禁止项见 [浓缩基线](baseline.md) / [openspec/baseline.md](../../openspec/baseline.md)。  
> 历次拍板见 [decisions.md](decisions.md)。

**最后核对**：2026-09-19 · `image-viewer-cross-page` 已落地（切图跟当前网格分页；待手验）。

---

## 一、项目实现（现状）

### 做什么（仓库里真实存在）

- 产品一句话：单机桌面工作台的**第一形态**是本地媒体库（图片/视频）；后续在同一壳里扩展工作上下文、模型/游戏等类型，以及设计系统与 AI 资产。
- 已交付（用户可感知）：
  - 启动 Electron 窗口；主进程拉起本机 FastAPI；健康检查通过后才开窗。
  - 首页拉 `/library/overview` 展示按类型计数。
  - 图片/视频页虚拟网格 + 触底分页；点选后右侧信息栏展示通用元数据，可保存评分/分类/标签、弹窗编辑、换封面、确认后软删；**回收站页 / 多选批量 / 恢复 / 彻底删除库内包**已写（待 Electron 手工验 T10–T16）。
  - 顶栏「导入」向导：选类型与文件/文件夹，后端复制进库目录并写资源记录（sha256 去重）。
  - 番剧/AV：作品级 Resource + 季集树；目录导入；信息栏选集播放（A-min；整理/字幕组/女优仍 OUT）。
- **尚未实现**（需求有、代码无或仅 health）：
  - 壳层运行时主题 / 外置 css / 顶栏批量条（`ui-theme-shell` 已合入 master，待 Electron 手工验）。
  - 库内搜索与排序（规划：`library-search-sort`，开放问题未关）。
  - 音频 / 小说 / 游戏 / 模型 / 漫画的类型与最低打开（`library-type-platform` 已合入 master，待 Electron 手工验）。
  - 视频专项（封面抽帧已并入规划 `library-covers` 本刀：新导入抽一帧；旧库不回填）、抓取（M3）、检索打标（M4）、下载引擎（M5）、设置（含库路径，M6）、全局 Notify、token 校验。
          - 图片查看器：`image-consume` + `image-viewer-ux` + `image-viewer-cross-page`（切图跟当前网格 keyset；待手工验跨页/拖拽缩放）。
  - scrape / download 子路由目前只有 `/health`。
  - 网格封面：新导入写包内 `thumbs/grid.webp` 并由列表 `thumbnailPath` 提供；旧资源仍可能拉原图。窗口缩放已节流，待手工验。

### 怎么做的（路径级）

| 层 | 技术 | 目录 / 入口 | 备注 |
|----|------|-------------|------|
| 桌面壳 | Electron 44 + TS | `apps/desktop/src/main` | `spawn` uvicorn；动态端口；`additionalArguments` 注入 URL/token |
| UI | Vue 3 + Vite + naive-ui + Pinia + vue-router | `apps/desktop/src/renderer/src` | 四层：`ui` / `application` / `domain` / `infrastructure` |
| 后端 | FastAPI + uvicorn | `apps/backend/app/main.py` | **一个进程**，`include_router`：`/library` `/scrape` `/download` |
| 数据 | SQLite + SQLAlchemy async + aiosqlite | `apps/backend/app/shared/db` | WAL；启动 `ensure_db`；**新库不再 demo seed** |
| 鉴权 | 主进程生成 token，axios Bearer | 后端**未校验** | 与需求「token 鉴权」不一致 |

- 主数据流：渲染进程 axios → `http://127.0.0.1:<port>/library/...` → `LibraryQueryService` → `ResourceRepository` → SQLite。
- 关键模块：
  - `apps/desktop/src/main/infrastructure/services/` — 端口、配置、spawn、停进程
  - `apps/backend/app/library/api/` — health / overview / resources / imports
  - `apps/desktop/src/renderer/src/hooks/useResourcePage.ts` — 分页列表状态
  - `apps/desktop/src/renderer/src/application/stores/selection.ts` — 当前选中 id
- 构建 / 启动：见浓缩基线。

### 实现边界（已确认）

- 本仓负责：桌面壳、本机后端、SQLite 资源库、后续自建抓取与内置下载编排。
- 本仓不负责：移动端、多用户账号、在线流媒体服务、资源分享。
- 已知债（有路径）：
  - `useResourceHandle.refreshResourceList` 不更新 `useResourcePage.items` — 已由 `library-trash` 用 `library.bump(null)` 让列表 reset（待手工验网格）。
  - README 仍写「无业务代码 / mount 双应用」，与现状不符。
  - 路线图 `docs/design/00-路线图与里程碑.md` 进度表已按 2026-09-19 核对（入库改道为导入；MS2 主路径完成）。
  - 导入 `phase=probe`：Pillow 宽高与 **EXIF 拍摄时间**；ffprobe 视频字段。图片拍摄可 PATCH 手改。缺列面板「—」。开发阶段以清库重导代替回填。

---

## 二、项目方向（已确认 · 2026-09-12 叠加 L1）

### 要成为什么

- **近端（A · 媒体库）**：每种库类型先具备 **导入 + 最低消费**。类型含图片、视频、番剧、AV、音频、小说、游戏、模型、**漫画**。漫画为本刀独立 type（D-20260917-02）。小说/漫画内置阅读器另立项。音频/模型用成熟库内置播/预览。游戏默认扫描登记源路径（D-20260917-03）。抓取、下载、合集后置。
- **中段（B · 不完整工作台）**：在 A 可用之后，加工作目录 + 消费渠道（按类型打开），**不是** WCH 草案的完整形态。
- **远期可扩展类型**：模型文件（含预览）、游戏（单机 / Gal / 黄油等）。菜单占位可早出现，能力按类型插件化加。
- **功能模块骨架**（规划用，未逐项定稿）：见 [module-map.md](module-map.md)。
- **远期资产域**（不挡 A）：设计系统管理、AI 提示词、Skill、导出。
- 明确不做（方向级）：在线播放平台、移动端、多用户、对外社交分享；下载不含 ED2K/WebDAV。

### 原则（已拍板）

- 产品：单机本地优先；先闭环媒体库，再长工作台；类型与资产域可插拔，避免为远期功能改死核心模型。
- 导入：用户选择文件或目录**一次**；媒体默认**复制**进库并写库、算元数据；**游戏默认只登记路径**（可选手动复制）。**新导入 owned 包内生成网格缩略图**（`thumbs/grid.webp`）；前端只选路径。不做常驻监视，**不把源目录登记为可再扫的根**。
- 分类与标签为**独立词表**；资源面板可新建词条并点保存挂上。词条统计/删除管理见 `tag-category-hygiene`（尚未实现）。
- 三栏信息栏默认不折叠（L1，未改口）。
- 技术：Electron+Vue；单一 FastAPI 进程；SQLite；下载/抓取引擎选型仍以 L1 为准（未落地）。
- 契约：DB snake_case ↔ API JSON camelCase。JSON 业务响应统一信封 `{ code, status, message, data }`（成功 `code=0`）；文件流与 OpenAPI 不包；前端 axios 解开 `data`。

### 近期顺序

1. **A-min（所有库最低消费）**：各类型导入策略 + 列表/详情/回收站 + 该类型基本打开方式（图看、视频播、番剧/AV 选集播、音频播、小说读、游戏启动、模型预览或系统打开）。
2. 收口已有图/视频闭环缺口（列表与删除一致、播放稳定）。
3. **A-plus（按类型/跨类型高级）**：系列整理与档案字段、词表与搜索、合集、抓取（M3）、下载（M5）、画廊沉浸。
4. **B 不完整工作台** 仅在 A-min 可用之后定稿再编码。
5. 设计系统、提示词、Skill、导出：远期资产域，单独立项。

与单功能稿冲突时：以本文**已确认**方向为准。WCH 全文定稿前，不得按完整 B 开工。高级能力不得插队挡住「某类型还不能打开」。

---

## 未确认

- 导出的第一刀导出什么（资源库备份 / 设计系统包 / 提示词与 Skill 包）。
- 设计系统、提示词、Skill 是独立顶栏域，还是「资源类型」的一种。
- 后端是否必须校验 `BACKEND_TOKEN`。
- 新能力是否一律 `features/<id>/需求.md`；三个早期 change 是否 archive。
- metadata-panel 桌面手工验收（T7–T12）尚未在本环境用 Electron 点完。
- 参考产品全功能对照与路线见 [reference-landscape.md](reference-landscape.md)；A-min 已拍板（D-20260917-01）。库类型打开方式见 D-20260917-02。

改实现或改方向：先记 `decisions.md`，再改本文对应句。
