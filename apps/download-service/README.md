# download-service · 下载服务（FastAPI）

独立后端进程，提供内置下载能力（双引擎）。见 `docs/requirements/features/lrm-tech-stack.md`。

## 分层结构

| 目录 | 层 | 职责 |
|------|-----|------|
| `app/api` | 接口适配层 | FastAPI 路由，面向 UI 契约 |
| `app/application` | 业务层 | 任务队列 / 协议路由 / 调度 |
| `app/domain` | 领域层 | 任务实体与引擎端口接口 |
| `app/infrastructure` | 基础设施层 | aria2 / rqbit / yt-dlp / SQLite |

## 启动

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

或从仓库根目录：`pnpm download:start`
