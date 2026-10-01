# 03 · API 设计（契约真源）

> 状态：**现状快照（2026-09-27）**。以代码为准；本文件与代码不一致时，先改本文件再改代码（G4）。
> 权威约束见 [`openspec/baseline.md`](../../openspec/baseline.md)；编码约定见 [`../standards/coding-conventions.md`](../standards/coding-conventions.md)。
> 数据表见 [`02-数据模型.md`](02-数据模型.md)；分页见 [`05-资源分页与无限滚动.md`](05-资源分页与无限滚动.md)。

## 1. 总则

| 项 | 约定 | 落点 |
|----|------|------|
| 绑定 | 只绑 `127.0.0.1`，单一 FastAPI 进程 | `app/main.py` |
| 前缀 | `/library` `/scrape` `/download` `/settings` 由 `include_router(prefix=...)` 挂入；不开 `/v1` | `app/main.py` |
| 命名 | Python/SQLite `snake_case` ↔ JSON `camelCase`，经 `ApiModel`（`alias_generator=to_camel`） | `app/shared/models.py` |
| 成功信封 | `{ code: 0, status: "success", message: "ok", data: <业务体> }` | `app/shared/api_envelope.py` |
| 失败信封 | `{ code: <HTTP 状态>, status: "error", message: <文案>, data: <详情或 null> }` | 同上 |
| 不包信封 | 文件流（`FileResponse`/`StreamingResponse`）、非 JSON、204、`/docs` `/redoc` `/openapi.json` | `ENVELOPE_SKIP_PATHS` |
| 前端解包 | axios 拦截器只回 `data`，业务代码不感知信封 | `renderer/src/infrastructure/http/client.ts` |
| 鉴权 | 主进程生成随机 token 经 `additionalArguments` 注入，axios 带 `Bearer`；后端**在配置了 `BACKEND_TOKEN` 时校验**，豁免见 §1.1；token 为空 = 未启用（仅开发态） | `shared/middleware/auth.py` |
| 401 形状 | `401` + `{code:401,status:"error",message:"未授权",data:null}` | 同上 |

错误文案约定：路由内 `HTTPException(status_code, detail="<人话>")`；前端 `mapHttpError` 落到 `notify`。

### 1.1 鉴权豁免清单（`shared/constants.py`）

| 规则 | 覆盖 |
|------|------|
| 后缀 `/health` | `/health`、`/library/health`、`/scrape/health`、`/download/health` |
| 前缀 `/docs` `/redoc` `/openapi.json` | OpenAPI 文档 |
| 后缀 `/content` | `/library/resources/{id}/content`、`/library/resources/{id}/files/{fileId}/content`（`img`/`video`/`model-viewer` 无法带请求头） |
| 全等 `/scrape/proxy-image` | 刮削封面代理（`<img>` 直链） |
| 方法 `OPTIONS` | CORS 预检：按规范不携带凭证，必须放行（且 CORS 中间件注册在最外层，401 也带 CORS 头） |

## 2. 根

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 主进程开窗前的就绪探针，只校验 HTTP 200 |

## 3. `/library` · 资源库

### 3.1 健康与概览

| 方法 | 路径 | 响应 | 说明 |
|------|------|------|------|
| GET | `/library/health` | `{status,app,version}` | 冒烟用 |
| GET | `/library/overview` | `Overview` | `stats`（`byType`/`totalSizeBytes`/`trashedCount`/`lostCount`）+ `recent` + `tasks` + `activeWork` + `recentConsumption` |

### 3.2 资源集合

`Resource` 主要字段：`id` `type` `storageKind` `title` `description`（用户评价）`synopsis`（作品简介）`catalog` `author` `rating`（0–10）`coverPath` `thumbnailPath` `status` `deletedAt` `lastScrapedAt` `scrapedSource` `extra` `scrapePending` `createdAt` `updatedAt` `category` `tags` `files` `todos` `seasons` `extras`。

| 方法 | 路径 | 请求 | 响应 |
|------|------|------|------|
| GET | `/library/resources` | 查询参数见下 | `ResourcePage` |
| POST | `/library/resources` | `Resource` | `Resource`（直接入库，供内部/测试） |
| GET | `/library/resources/{id}` | — | `Resource`（含已 trashed） |
| PATCH | `/library/resources/{id}` | `ResourcePatch` | `Resource` |
| DELETE | `/library/resources/{id}` | — | `Resource`（**软删** → `trashed`） |
| POST | `/library/resources/{id}/restore` | — | `Resource`（非 trashed → 409） |
| POST | `/library/resources/{id}/purge` | — | `{ok: true}`（先删库内包再 DROP 行） |
| POST | `/library/resources/batch` | `{action, ids[1..200]}` | `{ok: int[], failed: [{id,message}]}`，部分失败仍 200 |

`GET /library/resources` 查询参数：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `type` | `ResourceType` | — | `image` `video` `anime` `av` `audio` `novel` `game` `model` `comic` `work_directory` |
| `status` | `active` \| `trashed` \| `lost` | — | 不传不过滤 |
| `limit` | 1–200 | 80 | |
| `offset` | ≥0 | 0 | 仅非 keyset 时生效 |
| `afterKey` + `afterId` | string + int | — | **keyset 游标**；两者齐备才走 keyset |
| `afterCreatedAt` | string | — | 旧字段，仅 `sort=createdAt` 时映射为 `afterKey` |
| `q` | ≤200 字 | — | 标题/作者/描述/分类/标签/文件名 LIKE |
| `tagIds` | int[] | — | 多选 **AND** |
| `sort` | `ResourceSortField` | `createdAt` | 非该类型允许值 → 422 |
| `order` | `asc` \| `desc` | `desc` | |

`ResourcePage` = `{ items, total, limit, offset, hasMore, nextCreatedAt, nextId, nextKey }`。触底追加用 `nextKey` + `nextId`。

### 3.3 文件内容

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/library/resources/{id}/content` | 流式返回 `role=primary` 副本；`Cache-Control: private, max-age=120` |
| GET | `/library/resources/{id}/files/{fileId}/content` | 包内指定文件；`role=thumbnail` 时 `max-age=86400` |

两个端点都只允许库目录内的文件，越界或缺失 → 404。返回的是**文件流**，不套信封。

### 3.4 封面、字幕、待办、笔记

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| POST | `/library/resources/{id}/cover` | `{path}` | 复制本机图片为包内 cover，**不动 primary**；类型不允许 → 422 |
| POST | `/library/resources/{id}/subtitles` | `{path}` | 仅 `video`；按原始视频名改名进包 `subtitles/` |
| POST | `/library/resources/{id}/todos` | `{content}` | 待办 |
| PATCH | `/library/resources/{id}/todos/{todoId}` | `{content?, done?}` | |
| DELETE | `/library/resources/{id}/todos/{todoId}` | — | |
| POST | `/library/resources/{id}/notes` | `{title?, content?}` | 工作目录备注 |
| DELETE | `/library/resources/{id}/notes/{noteId}` | — | |

### 3.5 导入

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/library/imports` | **202** + `{jobId}`；同一时刻只允许一个导入，冲突 → 409 |
| GET | `/library/imports/{jobId}` | `{jobId,status,phase,total,done,imported,skippedDuplicate,skippedError,error,message,code,details}` |

`ImportCreate` = `{type, sourceKind, paths[≥1], storageKind?}`。校验：不支持的 type/storageKind → 400；`series` 必须目录；`package` 必须目录（漫画可单文件 cbz/cbr）；目录只能 1 条路径且必须是目录。

### 3.6 词表与消费记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/library/categories` | `{items}` 只读 |
| GET | `/library/tags` | `{items}` 只读 |
| POST | `/library/work-directories` | `{path}` → 201 `Resource`（只登记，不复制不扫描） |
| POST | `/library/consumptions` | `{resourceId, action}` → `{ok:true}`，写入最近消费 |

## 4. `/scrape` · 元数据刮削

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/scrape/health` | |
| POST | `/scrape/jobs?force=<bool>` | `{resourceId, query?}`；复用未完成任务；`query` 非空必须能解析（如 BV）否则 400 |
| GET | `/scrape/jobs/{jobId}` | 任务状态：`queued/running/done/failed` |
| GET | `/scrape/jobs/{jobId}/candidates` | 候选列表（带 `source`） |
| POST | `/scrape/jobs/{jobId}/select` | 按字段勾选回填：`applyTitle` `applySynopsis` `applyAuthor` `applyTags` `applyCatalog` `applyCover` `replaceUserCover` |
| GET | `/scrape/jobs/{jobId}/candidates/{candidateId}/preview` | 详情预览 |
| GET | `/scrape/proxy-image?url=` | 封面代理（过公网校验，http 升 https） |
| GET | `/scrape/resources/{resourceId}/latest-job` | 无任务 → 404 |

**未选候选不写库**；`description`（用户评价）不被刮削覆盖。

## 5. `/download` · 下载

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/download/health` | |
| POST | `/download/tasks` | **201**；`{url}` 支持 HTTP(S) 直链与磁力；拒绝私网与带直链参数的磁力 |
| GET | `/download/tasks` / `/download/tasks/{id}` | 任务列表/单条 |
| POST | `/download/tasks/{id}/pause` \| `/resume` \| `/cancel` | 状态机 `queued/running/paused/done/failed` |

完成后经 `ImportService` 复制进视频库；sha256 重复则挂已有资源。

## 6. `/settings` · 设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/settings` | 刮削凭证（**掩码**）+ 系统路径 + 消费渠道 |
| PATCH | `/settings/scrape` | TMDB Key、Bangumi Token、蜜柑地址；env 优先且锁定 |
| PATCH | `/settings/consume` | 按类型的消费渠道（内嵌/系统/自定义命令） |
| PATCH | `/settings/system` | 系统项；**不含**改库根与扫描根 |
| POST | `/settings/backup` | SQLite backup API 到 `data/backups/` |

## 7. 待收口

- 缺口径变更（`docs/product/decisions.md`）后，本节与上文随实现同步更新。
