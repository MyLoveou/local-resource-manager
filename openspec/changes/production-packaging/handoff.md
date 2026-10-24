# 跨会话续作 · production-packaging

> 换会话先读本文再动手。结束未完成的会话必须更新。

## 状态

- change：`production-packaging`
- 阶段：`待验收`
- 最后更新：2026-10-07 · 流水线与自动校验全绿；安装包/dev 手工回归待跑

## 已完成

- tasks：1.1–1.3、2.1–2.2、3.1–3.2、4.1–4.2、5.1–5.2、6.1–6.2、7.1–7.2、8.1
- 自动证据：
  - `pnpm release:win` 退出 0：setup 135.7MB、zip 181.4MB、`SHA256SUMS.txt`
  - 冻结后端冒烟 `/health` 200、临时 DB 192KB
  - T4 失败演练：移走冻结后端 → verify exit 1 且无 SHA256SUMS
  - R1：typecheck/lint/pytest（177 passed）
  - R2：workflow YAML 解析通过
- 安装包反馈修复（2026-10-07）：
  - 应用图标：`build/icon.ico` + `build/generate-icon.py`（渐变圆角 + 媒体文件夹/播放）
  - 安装目录：`build/installer.nsh` 覆盖 `APP_FILENAME` → `%LOCALAPPDATA%\Programs\资源管理器`
  - 菜单图标：番剧 `television-classic`、合集 `folder-multiple`、AV `movie-open`
  - T5 PASS：静默安装/启动/卸载验证；程序目录移除、`%APPDATA%/local-resource-manager` 数据保留
- 实施要点：
  - Conda Python 3.14 的 OpenSSL/ffi/sqlite 等 DLL 在 `Library/bin`，spec 已显式收集
  - 渲染层依赖移到 devDependencies（Vite 已打包），asar 197.9MB → 9.8MB
  - 打包镜像：`ELECTRON_MIRROR` / `ELECTRON_BUILDER_BINARIES_MIRROR` 指向 npmmirror（本机网络）

## 下一步（新会话按此执行）

1. 手工 T6：`pnpm dev` 回归（venv 后端、仓库数据目录）
2. 通过后勾选 tasks 8.2；用户要求时 archive

## 阻塞

- 待你确认：`pnpm dev` 回归结果（T6；T5 已自动验证）
- 技术阻塞：无（GitHub Actions 首次运行未验证，需推送 tag/dispatch）

## 关键路径

- 规划：`openspec/changes/production-packaging/`
- 规范：`docs/requirements/features/production-packaging/需求.md`
- 设计：`docs/requirements/features/production-packaging/设计.md`
- 架构：`docs/requirements/features/production-packaging/实现方案.md`
- 代码：
  - `apps/desktop/electron-builder.yml`
  - `apps/desktop/src/main/infrastructure/services/{config,backend}.ts`
  - `apps/desktop/src/main/index.ts`
  - `apps/backend/run_server.py`、`apps/backend/packaging/backend.spec`
  - `apps/backend/app/shared/db/migrations.py`、`apps/backend/app/settings/api/router.py`
  - `scripts/release.mjs`、`scripts/verify-release.mjs`
  - `.github/workflows/release-windows.yml`
- 基线：`openspec/baseline.md`
- 事实：`docs/product/facts.md`
- 决策：`docs/product/decisions.md`

## 命令备忘

```powershell
pnpm exec openspec status --change "production-packaging" --json
pnpm release:win
pnpm release:verify
```

## 规范待决断（本 change 产生）

- 无
