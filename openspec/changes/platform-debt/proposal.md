# 提案 · platform-debt

> 与 `docs/requirements/features/platform-debt/需求.md` 同范围。只做 **D2 token 校验** 与 **D4 事件循环**；D1（Notify 迁移）与 D3（导入进度分相）已于 2026-09-27 落地，不在本 change。

## Why

两处能力与已拍板的口径不一致：

1. 主进程每次启动都生成随机 token 并经 `additionalArguments` 注入渲染进程、axios 已带 `Bearer`，但**后端完全不校验**；而且 `Settings.token` 字段名与 `BACKEND_TOKEN` 环境变量对不上，实际根本取不到值。需求写的是「进程间 token 鉴权」。
2. `platform-performance` 已写「Hash, copy, probe, and thumbnail SHALL run off the asyncio event loop」，但导入链上仍有 5 处同步 IO 直接在事件循环上跑（`comic_pages` / `find_launch` / `find_folder_cover` / `find_sidecar_cover` / `resolve_lnk_target`），导入大目录时会拖住同进程的 `/health` 与列表请求。

## What Changes

**D2 · 后端校验 `BACKEND_TOKEN`**

- 修正 `Settings` 的环境变量映射（`BACKEND_` 前缀），让 `BACKEND_TOKEN` 真正读得到。
- 新增 ASGI 中间件：非豁免路径校验 `Authorization: Bearer <token>`，失败返回 401 + 既有 JSON 信封。
- 中心化的**豁免清单**（配置在 `shared/constants.py`）：健康检查、OpenAPI 文档、**媒体字节流**（`*/content`）、`/scrape/proxy-image`。
- **token 为空 = 未启用鉴权**，启动打 `WARN` 日志（开发态 `pnpm backend:start` 保持可用；Electron 路径永远有 token）。

**D4 · 导入链同步 IO 移出事件循环**

- 上列 5 处调用改走 `asyncio.to_thread`。
- 检查清单写进 `实现方案.md`，供后续改后端时逐项核对。

**BREAKING：** 无。`DELETE` 语义、信封、路径、表结构均不变；只是新增 401 与把阻塞挪走。

明确不做：用户登录/多用户/权限模型；token 轮换 UI；HTTPS；把媒体端点改成签名 URL 或前端 blob；把导入搬进独立进程（另立项）。

## Capabilities

### New Capabilities

- `backend-access-control`：受保护路由要求 Bearer token；豁免清单居中声明；媒体端点免请求头；未配置 token 的行为与日志。

### Modified Capabilities

- （无。D4 不改 `platform-performance` 的要求文本——该 spec 早已写明「不得在事件循环上做 hash/copy/probe/thumbnail」，本 change 只是补齐实现缺口。）

## Impact

- 后端：`app/shared/config.py`（env 前缀）、`app/shared/constants.py`（豁免清单 + 匹配函数）、`app/shared/middleware/auth.py`（新）、`app/main.py`（装配中间件）、lifespan 增加未配置 WARN
- 后端行为：受保护路径无 token → 401；媒体/健康/文档路径不变
- 导入：`library/application/import_service.py`、`library/application/covers/ingest.py`
- 前端：**无改动**（axios 已带 Bearer；`<img>`/`<video>` 走豁免的媒体端点）
- 测试：新增 `apps/backend/tests/test_auth.py`；既有 159 项在 token 为空时不受影响
- 文档：`docs/design/03-API设计.md` §1 鉴权行、`openspec/baseline.md` 不变量、`README.md` 开发态说明
