# 测试 · metadata-panel-fields

| ID | 类型 | 期望 |
|----|------|------|
| T1 | 单测 | GET 含 author、todos、fps、bitrate |
| T2 | 单测 | `电影.zh.srt` 按原始 stem |
| T3 | 单测 | 图片 POST 字幕 400 |
| T4 | 手工 | 图片无字幕/帧率/码率/画质 |
| T5 | 手工 | 视频有时长清晰度分辨率帧率码率画质 |
| T6 | 手工 | 保存描述 |
| T7 | 手工 | 面板加字幕 |
| T8 | 单测 | 待办立刻写 |
| T9 | 单测 | 多语言并存 |
| T10 | 单测 | 1080×1920 → 清晰度 1080p |
| T11 | 单测 | 导入图有宽高（可用小 PNG fixture） |
| T12 | 单测 | mock 无 ffprobe 时视频仍导入 |
| T13 | 单测 | bpp 分档：缺码率 → 画质空；HEVC 加权 |

```powershell
pnpm --filter desktop typecheck
apps/backend/.venv/Scripts/python -m unittest tests.test_metadata_fields -v
```
