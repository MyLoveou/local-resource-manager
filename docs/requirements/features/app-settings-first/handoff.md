# 跨会话续作 · app-settings-first

## 状态

- 阶段：**已编码**（待 Electron 手验）
- 拍板：D-20260923-04
- 最后更新：2026-09-23

## 已完成

- L1/L2/L3
- GET/PATCH `/settings`、SQLite backup、TMDB/Bangumi/Mikan 读 KV
- 顶栏设置模态
- `unittest tests.test_settings` 通过

## 手测

设置填 TMDB Key 后视频刮削不再报未配置。系统页能打开日志目录并备份 db。有环境变量时该项只读。

## 不做

扫描根、改库路径、四空页签、下载限速。
