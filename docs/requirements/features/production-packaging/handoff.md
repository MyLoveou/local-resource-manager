# 跨会话续作 · production-packaging（能力目录）

> 与 `openspec/changes/production-packaging/handoff.md` 对齐。

## 状态

- 阶段：`待验收`
- 最后更新：2026-10-07 · 打包与校验流水线实现完成；自动项全绿；安装/ dev 手工回归待跑

## 已完成

- L1 `需求.md` 已定稿（五项范围确认）
- L2 `设计.md` 已确认
- L3 `实现方案.md` 已定稿
- 代码与流水线：运行时 dev/frozen 切换、PyInstaller 冻结、NSIS+zip、verify 脚本、CI
- 自动证据：`release:win` 退出 0；冻结后端 `/health` 200；T4 失败阻断；R1/R2 PASS
- 安装包反馈修复：应用图标、安装目录「资源管理器」、菜单图标；T5 PASS（安装/启动/卸载 + userData 验证）

## 下一步

1. 手工 T6：`pnpm dev` 回归
2. 通过后勾 tasks 8.2；用户要求时 archive

## 阻塞

- 待你确认：`pnpm dev` 回归结果
