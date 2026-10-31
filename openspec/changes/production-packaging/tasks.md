# 任务 · production-packaging

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

> 每项写明如何验证。官方 apply 靠 checkbox 追踪。

## 1. 对齐

- [x] 1.1 已读基线、`需求.md`、`设计.md`、`实现方案.md` 与本 change 的 proposal/specs/design/tests
- [x] 1.2 开放问题已关闭（五项范围已确认）
- [x] 1.3 实现不超出 `实现方案.md` 的文件清单

## 2. 运行时切换

- [x] 2.1 `config.ts` 增加 dev/frozen（`app.isPackaged`）；`backend.ts` 按 mode 组合命令/env；`main/index.ts` 打包态 userData ASCII 路径
- [x] 2.2 验证：`pnpm dev` 起后端；typecheck 通过

## 3. 冻结后端

- [x] 3.1 `run_server.py` + `packaging/backend.spec` + `requirements-packaging.txt` + `migrations.py` 冻结路径 + `_VERSION` 环境变量
- [x] 3.2 验证：PyInstaller 构建后直接 spawn exe → `/health` 200、临时 DB 生成

## 4. 安装包

- [x] 4.1 `electron-builder.yml`（nsis+zip、extraResources、ASCII 产物名）+ desktop `package.json` version/devDep
- [x] 4.2 验证：`electron-builder` 产物含 `resources/backend/source-manager-backend.exe`

## 5. 发布与校验脚本

- [x] 5.1 `scripts/release.mjs`（门禁→build→freeze→package→verify）+ `scripts/verify-release.mjs`（产物/版本/冒烟/SHA256）+ 根 scripts + `.gitignore`
- [x] 5.2 验证：`pnpm release:win` 零退出并生成 `SHA256SUMS.txt`

## 6. CI

- [x] 6.1 `.github/workflows/release-windows.yml`（windows-latest、setup-node/pnpm/python、`pnpm release:win`、upload-artifact）
- [x] 6.2 验证：本地等价命令通过；workflow 语法自检

## 7. 契约与文档

- [x] 7.1 无 API/数据模型变更；`facts.md` / `decisions.md` 同步
- [x] 7.2 两处 `handoff.md` 更新为「待验收」

## 8. 验收

- [x] 8.1 `tests.md` 自动项全部 PASS（贴命令与结果）
- [ ] 8.2 手工项（安装启动、zip 启动、dev 回归）由用户执行；未跑前不标「可交付」
