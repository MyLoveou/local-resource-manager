# 本地资源管理器

统一管理本地多种资源（图片、视频、番剧、AV、音频、小说、漫画、游戏、模型）的桌面应用：导入入库、元数据抓取、监视目录自动导入。下载不自建，统一委托第三方成熟下载器（D-20261007-01）。

## 技术栈

| 模块 | 技术 | 位置 |
|------|------|------|
| 桌面端（UI 层） | Electron 44 + Vue 3 + Vite 8（TS） | `apps/desktop` |
| 后端服务 | Python FastAPI（单进程：library / scrape / settings） | `apps/backend` |
| 存储 | SQLite（WAL + 迁移） | `apps/backend/data/library.db` |
| 监视导入 | watchdog + 事件桥（按类型派发、补扫、自动导入） | `apps/backend/app/shared/utils/watch_*` |

需求与决策：`docs/product/facts.md`（事实基线）、`docs/product/decisions.md`（决策记忆）、`docs/requirements/features/`（L1 需求）。

学习与经验：`docs/经验总结/README.md`（架构、进程、SQLite、发布、自动更新、媒体领域、学习路线）。

## 目录结构（四层：基础设施 / 领域 / 业务 / UI）

```
apps/
├── desktop/                    # UI 层（Electron + Vue）
│   └── src/
│       ├── main/               #   Electron 主进程（进程编排 / 服务拉起）
│       ├── preload/            #   安全桥（backend 地址注入）
│       └── renderer/src/       #   Vue 渲染进程
│           ├── ui/             #     UI 层：布局/视图/组件
│           ├── application/    #     业务层：stores/hooks
│           ├── domain/         #     领域层：类型与常量
│           └── infrastructure/ #     基础设施层：http/ipc
└── backend/                    # 后端服务（FastAPI 单进程）
    └── app/
        ├── main.py             #   入口：/library /scrape /settings + /health
        ├── shared/             #   共享层：config/db/constants/errors/utils
        ├── library/            #   资源库应用（导入/资源/概览/监视端点）
        ├── scrape/             #   抓取应用（TMDB/Bangumi/B站/OG）
        └── settings/           #   设置应用（凭证/系统路径/监视目录）
```

## 启动

```bash
pnpm dev                  # 桌面端（自动拉起后端）
pnpm backend:install      # 首次：建 venv + 装依赖
pnpm backend:start        # 独立起后端 :8000
pnpm --filter desktop typecheck
pnpm --filter desktop lint
pnpm --filter desktop build
```

```bash
# 后端测试
apps/backend/.venv/Scripts/pip install -r apps/backend/requirements-dev.txt
apps/backend/.venv/Scripts/python -m pytest -q apps/backend/tests
```

> pip 网络受限时：`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`
> 鉴权：桌面启动时主进程生成随机 token 注入后端；`pnpm backend:start` 裸跑无 token 时不校验鉴权（仅本机排障）。

## 工作流约定

- 新需求：需求沉淀（L1 定稿）→ 设计（L2，复杂必做）→ 实现方案（L3）→ 用户确认 → 编码
- 方向/实现变更：记 `docs/product/decisions.md` + 同轮更新 `facts.md`
- 变更通过 `openspec` 流程提出
