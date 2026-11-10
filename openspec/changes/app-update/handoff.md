# 跨会话续作 · app-update

## 状态

- change：`app-update`
- 阶段：`待发布验证`
- 最后更新：2026-10-18 · 0.1.1 带 updater 已打包；完整更新需发布 0.1.2

## 已完成

- electron-updater 主进程服务/事件/IPC；启动 8s 检查
- preload update API；渲染 store/横幅/设置页「更新」Tab
- 版本 0.1.1；electron-builder publish github；latest.yml/app-update.yml
- CI tag `v*` 发布 Release；verify 校验更新元数据
- 无 Release 时 404 可读提示（已实测）

## 下一步

1. 手动安装 0.1.1（0.1.0 无 updater）
2. 改版本 0.1.2 → push tag `v0.1.2` → CI 发布 Release
3. 0.1.1 安装版验证：公告 → 下载 → 重启 → 0.1.2
4. 签名（可选，后续）

## 阻塞

- 待 GitHub Actions / Release 发布
- 未签名，接受 SmartScreen

## 关键路径

- 规划：`openspec/changes/app-update/`
- 规范/设计：`docs/requirements/features/app-update/`
- 代码：`main/infrastructure/services/update.ts`、`UpdateBanner`、`SettingsModal`、`electron-builder.yml`、workflow
