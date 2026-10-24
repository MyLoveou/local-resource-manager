# 提案 · app-update

> 对照：`docs/requirements/features/app-update/需求.md` / `设计.md`（已定稿）

## 为什么

- 每次改动都要手动重装安装包；应用内没有检查/下载/安装入口
- 版本一直 0.1.0，即使有 updater 也无法识别新版本
- 用户需要更新公告（发布说明）

## 做什么

- 接入 `electron-updater`：启动静默检查 + 设置页手动检查
- 发现新版本：横幅展示版本与更新公告，用户确认后下载
- 下载完成：重启安装；数据在 `%APPDATA%` 保留
- GitHub Releases 作为更新源：CI 在 tag `v*` 时创建 Release 并上传安装包/latest.yml/blockmap/SHA256
- 版本 0.1.1（首个带 updater 的版本，需手动装一次）；之后 0.1.2+ 可应用内更新
- **BREAKING**：无

## 范围

| | 内容 |
|--|------|
| IN | 检查/公告/下载/安装；GitHub Releases；设置页更新 Tab；CI 发布 |
| OUT | 签名/公证、灰度/强制更新、差分更新、macOS/Linux、绿色 zip 自动更新 |
| 假设 | 无（用户确认现在实现） |

## 能力（Capabilities）

### 新增

- `app-update`：Windows 安装版应用内更新与更新公告

## 规范对齐

- 基线：单机桌面、Electron 主进程、GitHub 仓库 → 遵守
- 动工门禁：L1/L2 已定稿
- 冲突：无

## 现状要点（有路径）

- `apps/desktop/src/main/index.ts` — 主进程服务编排
- `electron-builder.yml` — 产物/NSIS；无 publish 配置
- `.github/workflows/release-windows.yml` — 构建上传 artifact，不发布 Release
- `apps/desktop/package.json` — version 0.1.0

## 影响

- 依赖：`electron-updater`（dependencies）
- 构建：`publish: github`，`latest.yml` + `app-update.yml`
- IPC/前端：update 状态与操作；设置页新增「更新」Tab
- 文档：需求/设计/实现方案、facts/decisions

## 验收意图（详情在 tests.md）

- 主路径：0.1.1 检查 → 发现 0.1.2 → 公告 → 下载 → 重启 → 0.1.2
- 失败：无 Release 时 404 提示可读、不崩溃；网络错误可重试
- 回归：开发态显示「仅安装版支持自动更新」；不影响启动
