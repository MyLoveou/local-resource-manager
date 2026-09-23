## Why

资源写路径已经前后端分裂：列表/详情走 `/resources`，更新/删除走 `/resource`，前端却调用复数路径；仓储没有 `update`，删除还用布尔 `deleted` 绕过已有的 `trashed` 状态机。现在就要对齐，否则信息栏编辑/删除无法落地，后续 Router 拆分只会复制错误契约。

## What Changes

- 资源集合与单项路径统一为 `/library/resources` 与 `/library/resources/{id}`（**BREAKING**：去掉单数 `/library/resource/{id}`）。
- 更新改为部分字段 DTO（PATCH），不再接受整份领域模型当 PUT 体。
- 删除改为软删：`DELETE /library/resources/{id}` 调用 `to_trash()`，返回 `trashed` 资源；不引入 `deleted` 布尔字段。
- 去掉公开 `POST /library/dev/seed`（启动时空库已灌演示数据）。
- 前端 HTTP 与上述路径/动词对齐；写失败向上抛出，不再吞成 `null`。
- 领域模型去掉重复 `deleted_at` 与 `deleted` 布尔（若工作区已加入）。

不在本 change：URL `/v1`、token 校验、`mount` 改 `APIRouter`、前端壳层布局。

## Capabilities

### New Capabilities

- `library-resource-api`: 资源库 HTTP 契约（列表信封、单项读写、软删、错误语义）

### Modified Capabilities

- （无既有 main spec）

## Impact

- 后端：`library/api/routes.py`、`application/schemas.py`、`application/use_cases.py`、`infrastructure/repositories.py`、`shared/models.py`
- 前端：`infrastructure/http/resources.ts`、`hooks/useResourceHandle.ts`、相关导出
- 启动 seed 仍走 lifespan，不走 HTTP
