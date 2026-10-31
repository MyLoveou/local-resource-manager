# 任务 · app-update

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

## 1. 对齐

- [x] 1.1 已读需求/设计/基线
- [x] 1.2 开放问题关闭（现在实现、GitHub Releases、0.1.1）
- [x] 1.3 实现不超出文件清单

## 2. 主进程/预加载

- [x] 2.1 electron-updater 依赖 + update 服务/事件/IPC
- [x] 2.2 启动 8s 检查；开发态 unsupported
- [x] 2.3 preload update API

## 3. 渲染

- [x] 3.1 update store
- [x] 3.2 更新横幅（公告/进度/重启安装）
- [x] 3.3 设置页「更新」Tab

## 4. 构建与发布

- [x] 4.1 版本 0.1.1；electron-builder publish github
- [x] 4.2 release 脚本 `--publish never`
- [x] 4.3 CI tag 发布 Release
- [x] 4.4 verify 校验 latest.yml/app-update.yml

## 5. 验收

- [x] 5.1 typecheck/lint/build；后端 186 passed（回归）
- [x] 5.2 打包产物 0.1.1 + latest.yml + app-update.yml
- [x] 5.3 安装版检查：无 Release 时 404 可读提示，不崩溃
- [ ] 5.4 发布 0.1.2 Release 后完整更新手验（需 CI/GitHub）
