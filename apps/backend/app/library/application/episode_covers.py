"""每集封面的抽帧封装。

只负责「视频 → 一张 jpg」这一步；是否入库由调用方决定。
没有 ffmpeg 或抽帧失败一律返回 False，由 UI 回退作品封面（需求 A8）。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

FRAME_SECONDS = 3.0
COVER_WIDTH = 320


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_cover(
    video: Path,
    output: Path,
    *,
    at_seconds: float = FRAME_SECONDS,
    width: int = COVER_WIDTH,
) -> bool:
    """抽第 N 秒的一帧写到 output；失败返回 False，不抛异常。"""
    if not ffmpeg_available() or not video.exists():
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-ss",
        str(at_seconds),
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:-2",
        "-y",
        str(output),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except Exception:  # noqa: BLE001 - 抽帧失败不应影响导入
        return False
    return result.returncode == 0 and output.exists() and output.stat().st_size > 0
