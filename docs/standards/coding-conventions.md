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

## 后端

- 新路由挂对应域 `APIRouter`，由 `main.py` `include_router`
- 迁移：`apps/backend/app/shared/db/migrations/`
- 不把 seed 做成公开 POST
