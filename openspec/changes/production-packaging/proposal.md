# 提案 · production-packaging

> 对照：`docs/requirements/features/production-packaging/需求.md`（已定稿，同范围）

## 为什么

- 当前只有开发态：`electron-vite build` 产出 JS，后端依赖仓库 venv 的 Python；无安装包、无校验流水线
- 目标用户机器不应安装 Python/Node；需要一个可安装的 Windows 生产包与可重复的打包/校验流程
- 不做的后果：无法分发、无法在干净机器验收，发布靠手工

## 做什么

- Windows x64：NSIS 安装包 + 绿色版 zip，内置 PyInstaller 冻结后端
- 生产态自动使用随包后端；DB/库包/日志落 `%APPDATA%/local-resource-manager`
- `pnpm release:win` 一条命令完成门禁、构建、冻结、打包、校验；失败非零退出
- `SHA256SUMS.txt`；冻结后端 `/health` 冒烟作为强制校验
- GitHub Actions（windows-latest）构建并上传 artifact
- 开发态 `pnpm dev` 行为不变
- **BREAKING**：无

## 范围

| | 内容 |
|--|------|
| IN | NSIS + zip；PyInstaller onedir；userData；本地+CI 校验；版本 0.1.0；中文产品名 |
| OUT | macOS/Linux；签名/公证；自动更新；安装器无人值守冒烟；自定义图标 |
| 假设 | 无（已确认） |

## 能力（Capabilities）

### 新增

- `production-packaging`：Windows 生产包构建与校验流水线

## 规范对齐

- 基线条目：单机桌面；单一 FastAPI 进程；SQLite；不提交构建产物 → 遵守
- 动工门禁：L1 已定稿；L2 已确认
- 冲突：无

## 现状要点（有路径）

- `apps/desktop/src/main/infrastructure/services/config.ts` — venv python + 仓库后端目录（仅开发态）
- `apps/desktop/src/main/infrastructure/services/backend.ts` — spawn `python -m uvicorn`
- `apps/backend/app/shared/db/migrations.py` — `Path(__file__)` 相对 migrations（冻结态需 `sys._MEIPASS`）
- `apps/desktop/src/main/log/index.ts` — 生产态已用 userData/logs
- `todo.md` P5 — 只提 Windows 打包方向；无现成 electron-builder/CI

## 影响

- 配置：`electron-builder.yml`、`requirements-packaging.txt`、根脚本
- 前端路由/API/表：无
- 依赖：新增 `electron-builder`（dev）、`pyinstaller`（打包 venv）
- 文档：需求/设计/实现方案、OpenSpec change、facts/decisions

## 验收意图（详情在 tests.md）

- 主路径：`pnpm release:win` 零退出；安装包/zip/SHA256 齐全；冻结后端 `/health` 200 且 DB 生成
- 失败路径：任一门禁或冒烟失败 → 非零退出
- 回归：`pnpm dev` 行为不变

## 开放问题

1. 无（已确认）
