# backend · 后端服务（FastAPI，单进程多应用）

独立后端进程，内挂**多个子应用**（FastAPI mount）。见 `docs/requirements/features/lrm-tech-stack.md` 与 `docs/design/02-数据模型.md`。

## 结构

```
app/
├── main.py              # 入口：挂载 /library /scrape /download + /health；lifespan 建库迁移
├── shared/              # 共享层
│   ├── config.py        #   配置（端口/token/db_path）
│   ├── constants.py     #   领域常量（Protocol/Engine/AdapterKey）
│   ├── models.py        #   共享实体（Resource/ResourceFile/Tag/Settings/SiteAdapter）
│   ├── value_objects.py #   值对象（Rating/Dimension/Progress）
│   ├── errors.py        #   领域异常
│   └── db/              #   SQLite：连接(WAL) + 迁移执行器 + migrations/
├── library/             # 资源库应用（概览/资源查询）
│   ├── api/             #   路由（/overview /resources）
│   ├── application/     #   用例 + DTO（LibraryQueryService / Overview）
│   ├── domain/          #   复用 shared 实体
│   └── infrastructure/  #   仓储实现（ResourceRepository / TaskSummaryRepository）
├── scrape/              # 抓取应用
└── download/            # 下载应用
```

## 端点

| 路径 | 说明 |
|------|------|
| `/health` | 后端总健康检查 |
| `/library/health` · `/overview` · `/resources` | 资源库应用（概览/资源） |
| `/scrape/health` | 抓取应用 |
| `/download/health` | 下载应用 |

## 数据存储

- SQLite 单文件 `apps/backend/data/library.db`（WAL + foreign_keys + busy_timeout）
- 启动时自动建库并执行 `shared/db/migrations/*.sql`（`schema_version` 追踪版本）
- 仓储层：`library/infrastructure/repositories.py`；DB 列 snake_case ↔ API JSON camelCase

## 启动

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

或从仓库根目录：`pnpm backend:start`
