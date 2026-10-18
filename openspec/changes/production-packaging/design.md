# 设计 · production-packaging

> L3 施工（HOW）。L2 见 `docs/requirements/features/production-packaging/设计.md`。
> 与 `docs/requirements/features/production-packaging/实现方案.md` 同一套文件清单。

## 上下文

- 现状：`electron-vite build` 仅 JS；主进程用 venv `python -m uvicorn`；无 electron-builder/CI
- 基线 / 约定：单一 FastAPI 进程；SQLite；构建产物不入库；前端四层；后端四层
- 生产态日志目录已由 `main/log/index.ts` 指向 userData

## 与现有架构对齐

- 沿用：主进程 `infrastructure/services`（配置/进程编排）；后端 `app` 包与 migrations；根级脚本目录新建 `scripts/`
- 落在现有模块：`config.ts`、`backend.ts`、`main/index.ts`、`app/shared/db/migrations.py`、`settings/api/router.py`
- 不新开分层：无新服务/新库；`scripts/` 只是构建编排（不进产品运行时）
- 摸底证据：已读 `config.ts`、`backend.ts`、`main/index.ts`、`log/index.ts`、`migrations.py`、`requirements.txt`、`electron.vite.config.ts`、根/desktop `package.json`

## 目标 / 非目标

**目标：** 生产包可安装可运行；一条命令构建+校验；失败阻断；开发态不变

**非目标：** 多平台、签名、自动更新、安装器自动冒烟、图标定制；不重构既有业务模块

## 方案

### 模块与文件

| 路径 | 职责 | 新建/改 |
|------|------|---------|
| `apps/desktop/package.json` | version 0.1.0；electron-builder devDep；`dist` 脚本 | 改 |
| `apps/desktop/electron-builder.yml` | appId/productName/nsis+zip/extraResources/artifactName | 新 |
| `apps/desktop/src/main/index.ts` | 打包态 userData ASCII 路径 | 改 |
| `apps/desktop/src/main/infrastructure/services/config.ts` | dev/frozen 配置 | 改 |
| `apps/desktop/src/main/infrastructure/services/backend.ts` | 命令/参数/env 组合 | 改 |
| `apps/backend/run_server.py` | 冻结入口 | 新 |
| `apps/backend/packaging/backend.spec` | PyInstaller 描述 | 新 |
| `apps/backend/requirements-packaging.txt` | PyInstaller 固定版本 | 新 |
| `apps/backend/app/shared/db/migrations.py` | 冻结态 migrations 路径 | 改 |
| `apps/backend/app/settings/api/router.py` | `_VERSION` 读环境 | 改 |
| `scripts/release.mjs` | 发布编排（组合根） | 新 |
| `scripts/verify-release.mjs` | 产物校验/冒烟/SHA256 | 新 |
| `package.json`（根） | release 脚本 | 改 |
| `.github/workflows/release-windows.yml` | CI | 新 |
| `.gitignore` | `release/`、`apps/backend/build/` | 改 |

清单外不改。

### 组合根

- 组合于：`scripts/release.mjs`（调用门禁、PyInstaller、electron-builder、verify）
- 切片：运行时切换 / 冻结打包 / 安装包 / 校验（无 UI 切片）
- 最后一步：在 `release/win-unpacked` 上冒烟冻结后端并生成 SHA256，禁止只构建不校验

### 数据流

1. `app.isPackaged` → frozen 配置 → spawn `resources/backend/source-manager-backend.exe`
2. env：`BACKEND_TOKEN`、`BACKEND_VERSION`、`LOG_DIR`、`BACKEND_DB_PATH`
3. 后端 `ensure_db` → migrations（冻结 `_MEIPASS`）→ DB/库包落 userData
4. release：清理 → 门禁 → build → freeze → package → verify → SHA256

### 决策

| 决策 | 选择 | 为何不选备选 |
|------|------|----------------|
| 后端冻结 | PyInstaller onedir | onefile 首启慢/临时目录；内嵌 Python 体积与路径更复杂 |
| 运行时判定 | `app.isPackaged` | 不用 NODE_ENV：preview 也应走开发态 |
| userData | 显式 ASCII 目录 | 中文 productName 进路径会影响脚本与备份 |
| 产物命名 | ASCII + 版本 + arch | 中文文件名不利于 CI/校验 |
| 校验 | 独立 verify 脚本 | 可单独重跑；release 失败即阻断 |
| 不签名 | 无证书 | 接受 SmartScreen；后续可加 |

## 风险

| 风险 | 表现 | 缓解 |
|------|------|------|
| PyInstaller 漏 hiddenimports | 冻结后端启动崩 | spec 显式声明 + release 冒烟强制 |
| migrations 路径 | 首启空库/报错 | `sys._MEIPASS` + 冒烟断言 DB 生成 |
| electron-builder 下载失败 | 本机构建卡住 | 文档给镜像；CI 缓存；失败非零退出 |
| pnpm 符号链接 | electron-builder 收集依赖异常 | 使用 electron-builder 26；失败改用 hoisted 方案（留作备选，不在本刀） |

## 迁移与回滚

- 发布顺序：后端冻结 → Electron 打包（一次产物）
- 回滚：删除 release 产物与脚本改动；开发态不依赖新路径

## 注释与可维护性

- `config.ts` 注明 dev/frozen 判定与 env 覆盖
- `run_server.py` 注明参数与主进程约定
- `migrations.py` 注明冻结态路径来源
- `scripts/release.mjs` 步骤打印可读标签
