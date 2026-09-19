# 跨会话续作 · audio-embedded-cover

## 状态

- 阶段：已落地
- 最后更新：2026-09-19

## 已完成

- L1/L2/L3；`extract_audio_cover`；ingest AUDIO；单测含真实 ffmpeg 附加图

## 下一步

- 重启 Electron，导入带内嵌封面的 mp3/flac 验收网格

## 关键路径

- `covers/embedded.py`
- `covers/ingest.py` `audio_path`
