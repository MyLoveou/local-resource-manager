# backend · 后端服务（FastAPI，单进程双应用）

独立后端进程，内挂**两个子应用**（FastAPI mount）。见 `docs/requirements/features/lrm-tech-stack.md`。

## 结构

```
app/
├── main.py              # 入口：挂载 /scrape 与 /download 两个子应用 + /health
├── shared/              # 共享：config、db、通用工具
├── scrape/              # 抓取应用
│   ├── api/             #   接口适配层（路由）
│   ├── application/     #   业务层（用例编排）
│   ├── domain/          #   领域层（实体/端口）
│   └── infrastructure/  #   基础设施层（httpx/适配器/缓存）
└── download/            # 下载应用（同四层）
    ├── api/
    ├── application/
    ├── domain/
    └── infrastructure/
```

## 端点

| 路径 | 说明 |
|------|------|
| `/health` | 后端总健康检查 |
| `/scrape/health` | 抓取应用 |
| `/download/health` | 下载应用 |

## 启动

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

或从仓库根目录：`pnpm backend:start`
