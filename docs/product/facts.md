# 项目事实基线

> 只写**已确认**的实现与方向。推测标「未确认」。  
> 约束/禁止项见 [浓缩基线](baseline.md) / [openspec/baseline.md](../../openspec/baseline.md)。  
> 历次拍板见 [decisions.md](decisions.md)。

**最后核对**：2026-09-12 · 依据：仓库代码 + L1 定稿 + 用户口头拍板（先 A 后不完整 B，后续可扩展类型与设计/AI 资产）。

---

## 一、项目实现（现状）

### 做什么（仓库里真实存在）

- 产品一句话：单机桌面工作台的**第一形态**是本地媒体库（图片/视频）；后续在同一壳里扩展工作上下文、模型/游戏等类型，以及设计系统与 AI 资产。
- 已交付（用户可感知）：
  - 启动 Electron 窗口；主进程拉起本机 FastAPI；健康检查通过后才开窗。
  - 首页拉 `/library/overview` 展示按类型计数。
  - 图片/视频页虚拟网格 + 触底分页；点选后右侧信息栏展示通用元数据，可保存评分/分类/标签、弹窗编辑、换封面、确认后软删。
  - 顶栏「导入」向导：选类型与文件/文件夹，后端复制进库目录并写资源记录（sha256 去重）。
- **尚未实现**（需求有、代码无或仅 health）：
  - 视频专项（字幕/封面抽帧）、预览/播放/回收站完整流（M2 大部分）、抓取（M3）、检索打标（M4）、下载引擎（M5）、设置（含库路径，M6）、全局 Notify、token 校验。
  - scrape / download 子路由目前只有 `/health`。

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
  - `useResourceHandle.refreshResourceList` 不更新 `useResourcePage.items` — 删除后网格仍显示该卡。
  - README 仍写「无业务代码 / mount 双应用」，与现状不符。
  - 路线图 `docs/design/00-路线图与里程碑.md` 日期 2026-09-07，M2 描述已过时。

---

## 二、项目方向（已确认 · 2026-09-12 叠加 L1）

### 要成为什么

- **近端（A · 媒体库）**：本地图片/视频能扫、能看、能改、能回收站；再补抓取与下载。这是当前唯一可开工的产品形态。
- **中段（B · 不完整工作台）**：在 A 可用之后，加工作目录 + 消费渠道（按类型打开），**不是** WCH 草案的完整形态。
- **远期可扩展类型**：模型文件（含预览）、游戏（单机 / Gal / 黄油等）。菜单占位可早出现，能力按类型插件化加。
- **功能模块骨架**（规划用，未逐项定稿）：见 [module-map.md](module-map.md)。
- **远期资产域**（不挡 A）：设计系统管理、AI 提示词、Skill、导出。
- 明确不做（方向级）：在线播放平台、移动端、多用户、对外社交分享；下载不含 ED2K/WebDAV。

### 原则（已拍板）

- 产品：单机本地优先；先闭环媒体库，再长工作台；类型与资产域可插拔，避免为远期功能改死核心模型。
- 导入：用户选择文件或目录**一次**；后端**复制**进库目录并写库、算元数据；前端只选路径。不做常驻监视，**不把源目录登记为可再扫的根**。
- 分类与标签为**独立词表**；资源面板可新建词条并点保存挂上。词条统计/删除管理见 `tag-category-hygiene`（尚未实现）。
- 三栏信息栏默认不折叠（L1，未改口）。
- 技术：Electron+Vue；单一 FastAPI 进程；SQLite；下载/抓取引擎选型仍以 L1 为准（未落地）。
- 契约：DB snake_case ↔ API JSON camelCase。

### 近期顺序

1. 收口媒体库可感知闭环（含删除后列表与库一致）。
2. M1 导入复制入库（类型可扩展，先图+视频）→ M2 浏览/详情/回收站/预览播放。
3. M3 抓取 → M4 检索打标 → M6 设置（可先做「添加目录」）。
4. M5 下载可与 3 后段并行。
5. **B 不完整工作台** 仅在 A 能用之后定稿再编码。
6. 模型预览、游戏库、设计系统、提示词、Skill、导出、合集/系列/加密/画廊/主题：见 [module-map.md](module-map.md) 占位，**单独立项**后再写 `需求.md`。

与单功能稿冲突时：以本文**已确认**方向为准。WCH 全文定稿前，不得按完整 B 开工。

---

## 未确认

- 导出的第一刀导出什么（资源库备份 / 设计系统包 / 提示词与 Skill 包）。
- 设计系统、提示词、Skill 是独立顶栏域，还是「资源类型」的一种。
- 后端是否必须校验 `BACKEND_TOKEN`。
- 新能力是否一律 `features/<id>/需求.md`；三个早期 change 是否 archive。
- metadata-panel 桌面手工验收（T7–T12）尚未在本环境用 Electron 点完。

改实现或改方向：先记 `decisions.md`，再改本文对应句。
