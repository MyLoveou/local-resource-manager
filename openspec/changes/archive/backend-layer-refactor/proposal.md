# 提案 · backend-layer-refactor

## Why

后端按功能模块（library / download / scrape / settings / shared）垂直切片，但「模型、领域、工具」三类资产没有按限界上下文收敛：

- 所有 SQLAlchemy 表模型堆在单个 God File `shared/db/orm.py`（15 个 Row，横跨 4 个模块）。
- `shared/models.py` 把「API 基类 + library 实体 + settings 实体」混在一起。
- `shared/constants.py` 里 `Protocol / DownloadEngine`（download 专属）、`AdapterKey`（scrape/settings）、`SourceKind`（library 专属）只是被顺手放进来，并非真正共享。
- settings 模块缺 `domain / infrastructure`，其仓储与 `KEY_*` 常量游离在 `shared/infrastructure/settings_repo.py`。
- `shared/utils/` 全是未被生产代码引用的草稿/死代码，且 `_now()/_ts()` 在三个仓储里各抄一份。

## What Changes

- `shared/` 收敛为「共享内核」：只保留真正跨模块的 ApiModel 基类、错误、值对象、配置、日志、HTTP 横切、DB 连接/迁移、文件系统 FileOps、通用时间工具。
- 领域实体与枚举各归其位：library 实体回 `library/domain`，download/scrape 枚举回各自 `domain`，settings 补全 `domain/infrastructure`。
- SQLAlchemy 表模型按模块拆分到各自 `infrastructure/orm.py`，`shared/db` 只留连接与迁移注册。
- `shared/utils` 清理：删除草稿/死代码，抽出 `db_now()/db_ts()` 单一实现，消灭三处重复。

## Non-goals

- 不改数据库 schema（除 resources.md5→sha256 一列）、不改 API 路径与 JSON 契约（camelCase）、不改前端。
- 不在本 change 内做「跨模块 application 深 import 治理」（下载/抓取对 library.application 的依赖收敛），单独排期。
- 不做纯横向分层（所有 model/domain/utils 全局汇总到 app 根）。

## Impact

- 纯结构重构，行为零变化；验证靠既有测试套件 + 启动建库冒烟。

## 开放问题

- 是否把 `shared/` 重命名为 `core/`（改动面约 136 处 import；本 change 保留 `shared/` 名以降风险）。
- `AdapterKey` 当前仅被 settings 的 `SiteAdapter` 消费，随 `SiteAdapter` 归入 `settings/domain`；将来 scrape 若引用再上提共享内核。
