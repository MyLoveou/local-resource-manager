# 编码约定（存量）

> 从已落地代码与 `docs/经验总结/01-架构全景.md` 抽出。新约定先入 `decisions.md` 再改本文。

## 分层

- 桌面 renderer：`ui` / `views` / `components` → `hooks` + `application/stores` → `domain` → `infrastructure`
- 后端每域：`api`（薄路由）→ `application`（用例 + DTO）→ `infrastructure`（仓储）；实体规则在 domain / `shared/models`
- 禁止 domain 依赖 HTTP、Vue、SQLAlchemy Session 细节

## 命名与契约

- TS / JSON：camelCase；Python / SQL：snake_case
- 资源集合路径：`/library/resources`、`/library/resources/{id}`
- 列表：分页信封 `items/total/limit/offset/hasMore`，再包进统一 API 信封
- 统一 JSON 信封：`{ code, status, message, data }`。成功 `code=0` `status=success`；失败 `code` 对齐 HTTP 状态、`status=error`。文件流与 `/docs` `/openapi.json` 不包。前端 axios 拦截器解开 `data`，业务代码不感知信封。
- 更新：PATCH 部分字段；删除：软删

## 前端

- HTTP 只放 `infrastructure/http`；组件不直接拼 URL
- 跨页选中用 Pinia，不把 InfoPanel 嵌进列表组件
- 用户可感知错误最终走 Notify（设计已定、**实现未落地**）；过渡期不要再吞成 `null` 且不提示
- **类型分支用映射**：`ResourceType → 扩展名/对话框过滤/文案` 放 `domain/mediaTypes.ts`（后端 `app/shared/media_types.py`），调用处 `map[type]`，禁止 if/else 选表
- **导入来源**：`SourceKind.FILE` / `DIRECTORY`（`domain/constants.ts` 与 `shared/constants.py`）；隐藏项用 `HIDDEN_NAME_PREFIX` / `is_hidden_fs_name`，禁止比较 `"file"` / `"."` 字面量
- **不变量集中**：字符串、扩展名、超时、阈值、角色名等到 `domain/constants.ts` / `domain/mediaTypes.ts` / `domain/mediaLabels.ts`（后端 `shared/constants.py` / `shared/media_types.py` / `shared/media_labels.py`），业务代码只引用，不散落字面量

## 文件规模

- 手写生产代码单文件目标 **≤500 行**；超过 500 行视为拆分信号。
- 生产代码硬上限 **800 行**；新增文件超过 500 行直接失败。
- 测试文件目标 **≤700 行**，硬上限 **1000 行**。
- Vue 只统计 `<script>` + `<template>`，不把 `<style>` 计入。
- 生成代码、migrations、lock 文件、静态数据、第三方代码不纳入检查。
- 存量超标文件写入 `scripts/file-size-baseline.json` 作为基线；基线文件不得继续增长，大改时必须顺手拆分，新增文件不得加入基线。
- 行数只是拆分信号，不替代职责单一、函数长度和依赖方向审查。

检查命令：`pnpm check:file-size`；仅在明确拆分后更新基线时使用 `node scripts/check-file-size.mjs --update-baseline`。

## 后端

- 新路由挂对应域 `APIRouter`，由 `main.py` `include_router`
- 迁移：`apps/backend/app/shared/db/migrations/`
- 不把 seed 做成公开 POST
- **`async def` 里不得直接调用同步阻塞 IO**（`os.walk` / `iterdir` / `shutil.*` / `subprocess.run` / `PIL.Image.open` 等）；必须 `await asyncio.to_thread(...)`。单进程单事件循环，一处阻塞会拖住同一进程的 `/health` 与列表请求（D-20260927-06、`platform-performance`）
- 鉴权豁免清单集中在 `shared/constants.py` 的 `AUTH_EXEMPT_*` + `is_auth_exempt()`；不得在路由里写路径条件
