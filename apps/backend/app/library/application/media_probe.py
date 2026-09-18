"""导入后探测宽高/时长/帧率/码率。失败返回空字段，不抛给导入器。"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.shared.media_types import AUDIO_PROBE_TYPES, FFPROBE_BIN, FFPROBE_TIMEOUT_SEC, VIDEO_PROBE_TYPES
from app.shared.log import logger
from app.shared.models import ResourceType


@dataclass(frozen=True)
class ProbeFields:
    """可写入 files 行的探测结果。"""

    width: int | None = None
    height: int | None = None
    duration: float | None = None
    fps: float | None = None
    bitrate: int | None = None
    codec: str | None = None


def _parse_frame_rate(raw: str | None) -> float | None:
    if not raw or raw in {"0/0", "N/A"}:
        return None
    if "/" in raw:
        num_s, den_s = raw.split("/", 1)
        try:
            num, den = float(num_s), float(den_s)
        except ValueError:
            return None
        if den == 0:
            return None
        value = num / den
        return value if value > 0 else None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def probe_image(path: Path) -> ProbeFields:
    """Pillow 读宽高。"""
    try:
        from PIL import Image
    except ImportError:
        logger.warning("未安装 Pillow，跳过图片探测")
        return ProbeFields()
    try:
        with Image.open(path) as image:
            width, height = image.size
        return ProbeFields(width=width, height=height)
    except Exception as exc:
        logger.warning("图片探测失败 %s: %s", path, exc)
        return ProbeFields()


def probe_video(path: Path, *, ffprobe_bin: str | None = None) -> ProbeFields:
    """调用 ffprobe；找不到命令或失败则空。"""
    binary = ffprobe_bin or shutil.which(FFPROBE_BIN)
    if not binary:
        logger.warning("未找到 ffprobe，跳过视频探测")
        return ProbeFields()
    try:
        completed = subprocess.run(
            [
                binary,
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ],
            check=False,
            capture_output=True,
            timeout=FFPROBE_TIMEOUT_SEC,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffprobe 失败 %s: %s", path, exc)
        return ProbeFields()
    if completed.returncode != 0:
        err = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""
        logger.warning("ffprobe 非零退出 %s: %s", path, err)
        return ProbeFields()
    try:
        payload = json.loads(completed.stdout.decode("utf-8", errors="replace") or "{}")
    except json.JSONDecodeError:
        return ProbeFields()
    streams = payload.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None) or {}
    fmt = payload.get("format") or {}
    width = video.get("width")
    height = video.get("height")
    duration_raw = fmt.get("duration") or video.get("duration")
    bitrate_raw = fmt.get("bit_rate") or video.get("bit_rate")
    fps = _parse_frame_rate(video.get("avg_frame_rate")) or _parse_frame_rate(
        video.get("r_frame_rate")
    )
    try:
        duration = float(duration_raw) if duration_raw is not None else None
    except (TypeError, ValueError):
        duration = None
    try:
        bitrate = int(bitrate_raw) if bitrate_raw not in (None, "N/A") else None
    except (TypeError, ValueError):
        bitrate = None
    codec = video.get("codec_name")
    return ProbeFields(
        width=int(width) if isinstance(width, int) else None,
        height=int(height) if isinstance(height, int) else None,
        duration=duration,
        fps=fps,
        bitrate=bitrate,
        codec=str(codec) if codec else None,
    )


def probe_media(type_: ResourceType, path: Path) -> ProbeFields:
    """按资源类型探测。系列作品探测每集视频流。"""
    try:
        if type_ == ResourceType.IMAGE:
            return probe_image(path)
        if type_ in VIDEO_PROBE_TYPES or type_ in AUDIO_PROBE_TYPES:
            return probe_video(path)
    except Exception as exc:
        logger.warning("媒体探测失败 %s: %s", path, exc)
    return ProbeFields()
