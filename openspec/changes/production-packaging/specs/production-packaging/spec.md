## Purpose

为 Windows 桌面端提供可安装的生产包（NSIS 安装包与绿色版 zip），内置冻结的 FastAPI 后端，使未安装 Python/Node 的用户机器可直接运行；同时提供一条命令完成构建、冻结、打包、产物校验与 SHA256 的流水线，校验失败即阻断发布。

## ADDED Requirements

### Requirement: Windows 生产包

系统 SHALL 通过 `pnpm release:win` 产出 NSIS 安装包、绿色版 zip 与 `SHA256SUMS.txt`，安装包版本与 `apps/desktop/package.json` 一致；开发态 `pnpm dev` 行为不变。

#### Scenario: 主路径成功

- **WHEN** 在构建机执行 `pnpm release:win`
- **THEN** 依次通过 typecheck/lint/后端测试、前端构建、后端冻结、electron-builder 打包与校验，退出码 0，产出 `local-resource-manager-<version>-win-x64-setup.exe`、`local-resource-manager-<version>-win-x64.zip`、`SHA256SUMS.txt`
- **对应测试**：`tests.md` T1/T3/R1

#### Scenario: 冻结后端可独立启动

- **WHEN** 校验脚本用临时 DB/端口启动 `release/win-unpacked/resources/backend/source-manager-backend.exe`
- **THEN** `GET /health` 返回 200，SQLite 文件被创建，进程可被终止
- **对应测试**：`tests.md` T2

#### Scenario: 失败即阻断

- **WHEN** 任一门禁、冻结或冒烟失败
- **THEN** release 以非零退出，不生成 `SHA256SUMS.txt`
- **对应测试**：`tests.md` T4

### Requirement: 生产运行时路径

系统 SHALL 仅在 `app.isPackaged` 时启动随包后端，并把数据库、库包与日志写入 `%APPDATA%/local-resource-manager`；开发态继续使用仓库 venv 与 `apps/backend/data`。

#### Scenario: 生产态数据落 userData

- **WHEN** 安装包启动且后端就绪
- **THEN** `%APPDATA%/local-resource-manager/library.db` 与 `logs/` 存在，应用可导入并打开资源
- **对应测试**：`tests.md` T5

#### Scenario: 开发态回归

- **WHEN** 执行 `pnpm dev`
- **THEN** 后端仍以 venv Python 启动，数据仍在 `apps/backend/data`
- **对应测试**：`tests.md` T6

## MODIFIED Requirements

（无）

## REMOVED Requirements

（无）
