"""每集封面抽帧：复用 `covers/frame.extract_video_frame`，不重复实现 ffmpeg 调用。

这里只提供「按集生成封面」所需的薄封装：目标路径 + 失败语义（返回 False，
由调用方回退作品封面，见需求 A8）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.library.application.covers.frame import extract_video_frame
from app.library.domain.media_types import FFMPEG_BIN


def ffmpeg_available() -> bool:
    return shutil.which(FFMPEG_BIN) is not None


def extract_cover(video: Path, output: Path, *, duration: float | None = None) -> bool:
    """抽一帧存成 jpg；没有 ffmpeg 或抽帧失败返回 False（不抛异常）。"""
    if not ffmpeg_available() or not video.exists():
        return False
    return extract_video_frame(video, output, duration=duration)
