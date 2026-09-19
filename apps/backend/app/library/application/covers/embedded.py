"""从音频容器抽出内嵌封面。失败返回 False，不挡导入。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.shared.log import logger
from app.shared.media_types import FFMPEG_BIN, FFMPEG_TIMEOUT_SEC


def extract_audio_cover(audio: Path, dest_jpg: Path) -> bool:
    """第一条视频/附加图流；输出必须用 jpg 扩展名。"""
    binary = shutil.which(FFMPEG_BIN)
    if binary is None:
        logger.warning("未找到 ffmpeg，跳过音频内嵌封面")
        return False
    dest_jpg.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_jpg.with_name(f"{dest_jpg.stem}.part.jpg")
    try:
        completed = subprocess.run(
            [
                binary,
                "-y",
                "-i",
                str(audio),
                "-an",
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
            logger.warning("ffmpeg 抽内嵌封面失败 %s: %s", audio, err.strip() or completed.returncode)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            return False
        tmp.replace(dest_jpg)
        return True
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg 抽内嵌封面失败 %s: %s", audio, exc)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False
