# 本地资源管理器

统一管理本地多种资源（图片、视频等）的桌面应用：本地扫描入库、元数据自建抓取、内置下载器。

> 状态：**项目骨架**。需求沉淀见 `docs/requirements/`，技术方案（L3）未定稿前不写业务代码。

## 技术栈（已决策）

| 模块 | 技术 | 说明 |
|------|------|------|
| 桌面端 | Electron + Vue | 主进程 + 渲染进程，`apps/desktop` |
| 后端服务 | Python FastAPI | 元数据抓取等服务，`apps/backend` |
| 下载 | 内置下载器 | 方案待定稿 |
| 存储 | SQLite（倾向） | 待 L3 确认 |

## 目录规范

```
资源管理器/
├── docs/                          # 文档体系
│   ├── requirements/features/     #   L1 需求文档（需求沉淀维护）
│   └── design/                    #   L3 技术方案（plan-workflow 维护）
├── apps/
│   ├── desktop/                   # Electron + Vue 桌面端
│   │   ├── electron/              #   Electron 主进程
│   │   └── src/                   #   Vue 渲染进程
│   └── backend/                   # FastAPI 元数据服务
│       └── app/
│           ├── api/               #   路由层
│           └── services/          #   业务/抓取服务层
└── openspec/                      # spec-driven 变更工作流（已有）
```

## 工作流约定

- 新需求：先 `需求沉淀`（L1 定稿）→ 再 `plan-workflow`（L3 方案定稿）→ 用户确认 → 编码
- 变更通过 `openspec` 流程提出（propose → explore → update → apply）
