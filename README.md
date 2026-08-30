# 本地资源管理器

统一管理本地多种资源（图片、视频等）的桌面应用：本地扫描入库、元数据自建抓取、内置下载器。

> 状态：**项目骨架可启动**。需求（L1）已定稿，技术方案（L3）待产出，当前无业务代码。

## 技术栈（已定稿）

| 模块 | 技术 | 位置 |
|------|------|------|
| 桌面端（UI 层） | Electron 44 + Vue 3 + Vite 8（TS） | `apps/desktop` |
| 抓取服务 | Python FastAPI（SearXNG + 站点适配器） | `apps/scrape-service` |
| 下载服务 | Python FastAPI（aria2c + rqbit 双引擎） | `apps/download-service` |
| 存储 | SQLite（待 L3 数据模型） | — |

需求文档：`docs/requirements/features/`（主需求 / 模块 / 页面 / 技术栈，均已定稿）。

## 目录结构与分层

```
资源管理器/
├── apps/
│   ├── desktop/                    # UI 层（Electron + Vue）
│   │   └── src/
│   │       ├── main/               #   Electron 主进程
│   │       │   └── infrastructure/ #     进程编排 / 服务拉起
│   │       ├── preload/            #   安全桥
│   │       └── renderer/src/       #   Vue 渲染进程（四层）
│   │           ├── ui/             #     UI 层：布局/视图/组件
│   │           ├── application/    #     业务层：状态与用例
│   │           ├── domain/         #     领域层：类型与接口
│   │           └── infrastructure/ #     基础设施层：API client/IPC
│   ├── scrape-service/             # 抓取服务（FastAPI）
│   │   └── app/
│   │       ├── api/                #   接口适配层（路由）
│   │       ├── application/        #   业务层（用例编排）
│   │       ├── domain/             #   领域层（实体/端口）
│   │       └── infrastructure/     #   基础设施层（httpx/适配器/缓存）
│   └── download-service/           # 下载服务（FastAPI，同四层）
└── docs/
    ├── requirements/features/      # L1 需求（已定稿）
    └── design/                     # L3 技术方案（落点）
```

**统一分层约定**：基础设施层 / 领域层 / 业务层（application）/ UI 层。

## 启动

```bash
# 桌面端（开发模式，弹出 Electron 窗口）
pnpm dev

# 抓取服务（127.0.0.1:8001）
pnpm scrape:install      # 首次：建 venv + 装依赖
pnpm scrape:start

# 下载服务（127.0.0.1:8002）
pnpm download:install    # 首次
pnpm download:start
```

> pip 网络受限时：`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`

## 工作流约定

- 新需求：需求沉淀（L1 定稿）→ plan-workflow（L3 方案定稿）→ 用户确认 → 编码
- 变更通过 `openspec` 流程提出（propose → explore → update → apply）
