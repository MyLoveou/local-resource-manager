"""从视频抽一帧作封面。失败返回 False，不挡导入。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.shared.log import logger
from app.library.domain.media_types import (
    FFMPEG_BIN,
    FFMPEG_TIMEOUT_SEC,
)


def extract_video_frame(video: Path, dest_jpg: Path, *, duration: float | None = None) -> bool:
    """约第 1 秒；时长不足 1 秒则 0 秒。临时文件必须用图片扩展名，否则 ffmpeg 无法选 muxer。"""
    binary = shutil.which(FFMPEG_BIN)
    if binary is None:
        logger.warning("未找到 ffmpeg，跳过抽帧")
        return False
    seek = "0" if duration is not None and duration < 1 else "1"
    dest_jpg.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_jpg.with_name(f"{dest_jpg.stem}.part.jpg")
    try:
        completed = subprocess.run(
            [
                binary,
                "-y",
                "-ss",
                seek,
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(tmp),
            ],
            check=False,
            capture_output=True,
            timeout=FFMPEG_TIMEOUT_SEC,
            stdin=subprocess.DEVNULL,
        )
        if completed.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
            err = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""
            logger.warning("ffmpeg 抽帧失败 %s: %s", video, err.strip() or completed.returncode)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            return False
        tmp.replace(dest_jpg)
        return True
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg 抽帧失败 %s: %s", video, exc)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False
