# 跨会话续作 · download-magnet-aria2

## 状态

- 阶段：**已编码**（待 Electron 手验）
- 拍板：D-20260923-06
- 分支：`feat/ms7-download`
- 最后更新：2026-09-23

## 已完成

- 磁力校验与 aria2 JSON-RPC 客户端
- 完成后仍走 ImportService 进视频库
- `unittest tests.test_download_magnet` 

## 手测

本机有 aria2c 时：顶栏下载 → 贴磁力 → 完成后视频库可播。未安装时应提示「未找到 aria2」。HTTP 直链仍走 httpx。

## 不做

rqbit、yt-dlp、HTTP 改走 aria2、随包分发 aria2c。
