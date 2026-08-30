# scrape-service · 抓取服务（FastAPI）

独立后端进程，提供元数据抓取能力。见 `docs/requirements/features/lrm-tech-stack.md`。

## 分层结构

| 目录 | 层 | 职责 |
|------|-----|------|
| `app/api` | 接口适配层 | FastAPI 路由，面向 UI 契约 |
| `app/application` | 业务层 | 用例编排（检索/抓取/回填） |
| `app/domain` | 领域层 | 实体与端口接口 |
| `app/infrastructure` | 基础设施层 | httpx / SearXNG / 站点适配器 / 缓存 / SQLite |

## 启动

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

或从仓库根目录：`pnpm scrape:start`
