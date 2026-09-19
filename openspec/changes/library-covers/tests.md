# 测试 · library-covers

| ID | 步骤 | 期望 |
|----|------|------|
| T1 | 视频/音频/番剧/游戏信息栏更换封面 | 网格与面板更新；图片无该入口 |
| T2 | API 对图片 `POST /cover` | 422 |
| T3 | 导入无海报视频（本机有 ffmpeg） | 有 thumbnail；无 ffmpeg 仍导入成功、可无封面 |
| T4 | 番剧目录含 `poster.jpg` | 用海报，不抽帧 |
| T5 | 番剧无海报 | 有 ffmpeg 则用第一集帧 |
| T6 | 游戏目录仅 exe、无 poster | 网格有图标级缩略图 |
| T7 | 游戏目录有 `cover.png` | 用海报不用图标 |
| T8 | 游戏 launch 为 lnk 指向 exe（Windows） | 抽出目标图标 |
| T9 | 手换封面后再触发自动 apply（单测） | 文件不变，origin 仍 user |
| T10 | 导入音频 | 成功；无自动封面；可手指定 |
| R1 | 打开、软删、indexed 游戏彻底删除 | 不删源盘 exe |

## 记录

| ID | 结果 |
|----|------|
| 全部 | 未跑 |
