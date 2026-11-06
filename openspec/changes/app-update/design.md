# 设计 · app-update

> L3 HOW；L2 见 `docs/requirements/features/app-update/设计.md`。

## 上下文

- Electron 主进程已负责拉后端；preload 通过 contextBridge 暴露 API
- electron-builder NSIS 产物已有；无 publish/最新版本元数据
- 版本 0.1.1（首个 updater 版本）

## 与现有架构对齐

- 主进程：`main/infrastructure/services/update.ts`（新），`main/index.ts` 注册
- preload：新增 `update` API
- 渲染：`application/stores/update.ts` + `components/UpdateBanner` + `SettingsModal` 更新 Tab
- 构建/CI：`electron-builder.yml` publish；`release-windows.yml` tag 时发布
- 不引入新后端/数据库

## 方案

### 状态与 IPC

- `UpdateStatus`：phase / currentVersion / version / releaseNotes / percent / message
- `update:get-state` / `check` / `download` / `install`；`update:status` 推送
- `autoDownload=false`；启动 8s 后检查；开发态 unsupported

### 文件

| 路径 | 职责 |
|------|------|
| `apps/desktop/src/main/infrastructure/services/update.ts` | autoUpdater 初始化/事件/IPC |
| `apps/desktop/src/main/index.ts` | 注册与启动检查 |
| `apps/desktop/src/preload/index.ts` | update API |
| `apps/desktop/src/renderer/src/domain/update.ts` | 状态类型 |
| `apps/desktop/src/renderer/src/application/stores/update.ts` | 状态/动作 |
| `apps/desktop/src/renderer/src/components/UpdateBanner/index.vue` | 横幅/公告/进度 |
| `apps/desktop/src/renderer/src/components/SettingsModal/index.vue` | 更新 Tab |
| `apps/desktop/electron-builder.yml` | publish github |
| `scripts/release.mjs` | electron-builder `--publish never` |
| `.github/workflows/release-windows.yml` | tag 发布 Release |
| `scripts/verify-release.mjs` | 校验 latest.yml/app-update.yml |

### 决策

| 决策 | 选择 | 为何 |
|------|------|------|
| 更新源 | GitHub Releases | 仓库已有，CI 可发布 |
| 下载策略 | 先公告后下载 | 用户可控，避免后台偷跑 |
| 首次版本 | 0.1.1 手动装一次 | 0.1.0 无 updater |
| 签名 | 不做 | 无证书；接受 SmartScreen |

## 风险

- 未签名更新可能被拦截；文档说明
- 首次必须手动安装 0.1.1
- CI Release 需 `GITHUB_TOKEN` 权限 `contents: write`
- 无 Release 时 404 需可读提示（已映射）

## 迁移与回滚

- 发布顺序：0.1.1 手动安装 → 后续 tag 发布
- 回滚：禁用自动检查/发布旧版；数据不迁移
