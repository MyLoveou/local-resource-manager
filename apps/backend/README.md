# backend · 后端服务（FastAPI，单进程多应用）

独立后端进程，内挂**多个子应用**（FastAPI mount）。见 `docs/requirements/features/lrm-tech-stack.md` 与 `docs/design/02-数据模型.md`。

## 结构

```
app/
├── main.py              # 入口：挂载 /library /scrape /settings + /health；lifespan 建库迁移 + 监视器启动
├── shared/              # 共享内核（仅放真正跨模块的横切资产）
│   ├── config.py        #   配置（端口/token/db_path/watch_dirs）
│   ├── constants.py     #   HTTP/API 横切常量（鉴权豁免、envelope）
│   ├── models.py        #   ApiModel 基类（snake↔camel JSON 契约）
│   ├── value_objects.py #   值对象（Rating/Dimension/Progress）
│   ├── errors.py        #   领域异常（DomainError/InvalidStateError/DownloadError）
│   ├── log.py           #   日志
│   ├── api_envelope.py  #   统一响应包装 + 异常处理器
│   ├── middleware/      #   auth / logging
│   ├── fs/              #   FileOps（文件系统横切）
│   ├── db/              #   SQLite：base(Base) + 连接(WAL) + 迁移执行器 + migrations/
│   └── utils/           #   time / file_watcher / file_event_handler / watch_bridge / watch_manager / ssrf
├── library/             # 资源库应用（核心限界上下文）
│   ├── api/             #   路由（/overview /resources /watch-revision）
│   ├── application/     #   用例 + DTO
│   ├── domain/          #   实体 Resource/ResourceFile/Tag/Category/Series*/WorkCatalog + 类型档案/媒体映射
│   └── infrastructure/  #   本模块 ORM 表 + 仓储实现
├── scrape/              # 抓取应用
│   ├── api/ application/
│   ├── domain/          #   ScrapeJob/Candidate/ScrapeJobStatus
│   └── infrastructure/  #   ScrapeJobRow/CandidateRow + 仓储
└── settings/            # 设置应用
    ├── api/ application/
    ├── domain/          #   Settings/SiteAdapter/AdapterKey + KV key 常量
    └── infrastructure/  #   SettingsRow + SettingsRepository

> 下载应用已移除（D-20261007-01）：下载不自建，委托第三方成熟下载器；产物经监视目录入库。
> 监视链路：`shared/utils/watch_manager`（按类型配置/派发）→ `watch_bridge`（攒批 + 自动导入 + 启动补扫）→ `watch_events`（前端轮询修订号）。
```

## 端点

| 路径 | 说明 |
|------|------|
| `/health` | 后端总健康检查 |
| `/library/health` · `/overview` · `/resources` · `/watch-revision` | 资源库应用（概览/资源/监视修订号） |
| `/scrape/health` | 抓取应用 |
| `/settings` | 设置应用 |

## 数据存储

- SQLite 单文件 `apps/backend/data/library.db`（WAL + foreign_keys + busy_timeout）
- 启动时自动建库并执行 `shared/db/migrations/*.sql`（`schema_version` 追踪版本）
- ORM 表模型按限界上下文拆分到各 `infrastructure/orm.py`，共享 `shared/db/base.py` 的 `Base`
- 仓储层：各模块 `infrastructure/`；DB 列 snake_case ↔ API JSON camelCase

## 启动

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

或从仓库根目录：`pnpm backend:start`
