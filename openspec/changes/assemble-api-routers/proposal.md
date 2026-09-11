## Why

三个业务域用 `FastAPI.mount` 各挂一个完整子应用，library 的全部路由仍挤在一个 `routes.py`。同一进程、同一 SQLite 并不需要嵌套应用；不先改装配，后续 scrape/download 接口还会继续堆进单文件。

## What Changes

- 根应用改为 `include_router(prefix=...)`，不再 `mount` 三个子 FastAPI。
- library 按资源拆 `APIRouter`（health / overview / resources），由聚合 router 挂到 `/library`。
- scrape、download 同样改为 `APIRouter`（目前仅 health），为后续接口留同一装配方式。
- 对外 URL 保持 `/library/...`、`/scrape/health`、`/download/health`、`/health`。
- 不引入 `/v1`，不做 token 校验，不改前端壳层。

## Capabilities

### New Capabilities

- `http-app-assembly`: 单进程 FastAPI 如何把 library/scrape/download 装到根应用，以及稳定的 URL 前缀。

### Modified Capabilities

- （无）

## Impact

- `apps/backend/app/main.py`
- `apps/backend/app/library/api/`
- `apps/backend/app/scrape/api/routes.py`
- `apps/backend/app/download/api/routes.py`
- 前端路径不变
