# 跨会话续作 · platform-debt

## 状态

- 阶段：**实现中**（2026-09-27 apply 授权）
- 拍板：`D-20260927-06`（Q1–Q5）
- 最后更新：2026-09-27

## 已完成

- D1 全库提示迁 Notify、D3 导入进度分相（2026-09-27，独立于本 change）
- L1 `需求.md`、L2 `设计.md`、L3 `实现方案.md`

## 下一步

1. 按 `tasks.md` 落地 D2（token 校验）与 D4（5 处同步 IO 改 `to_thread`）。
2. 跑 `tests.md`：T1–T9 自动化 + T10 手工。
3. 同步 `03-API设计.md` / `baseline.md` / `README.md` / `facts.md`。

## 不做

用户登录与权限模型、token 轮换 UI、HTTPS、媒体端点改签名 URL 或前端 blob、把导入搬进独立进程。
