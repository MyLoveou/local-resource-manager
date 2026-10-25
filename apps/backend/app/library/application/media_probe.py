"""导入后探测宽高/时长/帧率/码率。失败返回空字段，不抛给导入器。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.library.domain.media_types import (
    AUDIO_PROBE_TYPES,
    FFPROBE_BIN,
    FFPROBE_TIMEOUT_SEC,
    VIDEO_PROBE_TYPES,
)
from app.shared.log import logger
from app.shared.image_support import register_optional_image_decoders
from app.library.domain.models import ResourceType


@dataclass(frozen=True)
class ProbeFields:
    """可写入 files 行的探测结果。"""

    width: int | None = None
    height: int | None = None
    duration: float | None = None
    fps: float | None = None
    bitrate: int | None = None
    codec: str | None = None
    audio_codec: str | None = None
    audio_channels: int | None = None
    audio_language: str | None = None
    exif_taken_at: str | None = None
    exif_lat: float | None = None
    exif_lng: float | None = None
    exif_camera: str | None = None
    exif_lens: str | None = None
    exif_iso: int | None = None
    exif_aperture: str | None = None
    exif_shutter: str | None = None


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


_EXIF_DT_ORIGINAL = 36867
_EXIF_DT_DIGITIZED = 36868
_EXIF_DT = 306
_EXIF_MAKE = 271
_EXIF_MODEL = 272
_EXIF_EXPOSURE = 33434
_EXIF_FNUMBER = 33437
_EXIF_ISO = 34855
_EXIF_ISO_SENSITIVITY = 34864
_EXIF_LENS_MAKE = 42035
_EXIF_LENS_MODEL = 42036
_EXIF_IFD = 0x8769
_EXIF_GPS_IFD = 0x8825
_TAKEN_AT_RE = re.compile(r"^(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?")


def normalize_taken_at(raw: str | None) -> str | None:
    """把 EXIF 或手填时间收成 YYYY-MM-DDTHH:MM:SS。非法则 None。空串清空。"""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    match = _TAKEN_AT_RE.match(text)
    if match is None:
        return None
    year, month, day, hour, minute, second = match.groups()
    try:
        y, mo, d = int(year), int(month), int(day)
        h, mi, s = int(hour), int(minute), int(second or "0")
    except ValueError:
        return None
    if not (1 <= mo <= 12 and 1 <= d <= 31 and 0 <= h <= 23 and 0 <= mi <= 59 and 0 <= s <= 59):
        return None
    if y < 1:
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}"


def _exif_taken_at(image) -> str | None:
    try:
        exif = image.getexif()
    except Exception:
        return None
    if not exif:
        return None
    nested: dict = {}
    try:
        nested = dict(exif.get_ifd(_EXIF_IFD) or {})
    except Exception:
        nested = {}
    for tag in (_EXIF_DT_ORIGINAL, _EXIF_DT_DIGITIZED, _EXIF_DT):
        raw = nested.get(tag) or exif.get(tag)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        if not isinstance(raw, str):
            continue
        parsed = normalize_taken_at(raw)
        if parsed is not None:
            return parsed
    return None


def _gps_coord(values, ref) -> float | None:
    """EXIF GPS 度分秒 → 十进制度；S/W 为负。"""
    if not isinstance(values, (list, tuple)) or len(values) < 3:
        return None
    try:
        deg, minute, sec = (float(values[0]), float(values[1]), float(values[2]))
    except (TypeError, ValueError):
        return None
    if isinstance(ref, bytes):
        ref = ref.decode("utf-8", errors="replace")
    if not isinstance(ref, str):
        return None
    result = deg + minute / 60 + sec / 3600
    if ref.strip().upper() in {"S", "W"}:
        result = -result
    return result


def _exif_text(raw: object) -> str | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace").rstrip("\x00")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    return text or None


def _exif_number(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (list, tuple)) and len(raw) == 2 and not isinstance(raw[0], (list, tuple)):
        try:
            num, den = float(raw[0]), float(raw[1])
        except (TypeError, ValueError):
            return None
        if den == 0:
            return None
        return num / den
    numerator = getattr(raw, "numerator", None)
    denominator = getattr(raw, "denominator", None)
    if isinstance(numerator, (int, float)) and isinstance(denominator, (int, float)):
        if denominator == 0:
            return None
        return float(numerator) / float(denominator)
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _exif_iso(raw: object) -> int | None:
    if isinstance(raw, (list, tuple)) and raw:
        raw = raw[0]
    value = _exif_number(raw)
    if value is None or value <= 0:
        return None
    return int(round(value))


def _format_camera(make: object, model: object) -> str | None:
    make_s = _exif_text(make)
    model_s = _exif_text(model)
    if make_s and model_s:
        if model_s.lower().startswith(make_s.lower()):
            return model_s
        return f"{make_s} {model_s}"
    return model_s or make_s


def _format_lens(make: object, model: object) -> str | None:
    return _format_camera(make, model)


def _format_aperture(raw: object) -> str | None:
    value = _exif_number(raw)
    if value is None or value <= 0:
        return None
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"f/{text}"


def _format_shutter(raw: object) -> str | None:
    value = _exif_number(raw)
    if value is None or value <= 0:
        return None
    if value >= 1:
        if abs(value - round(value)) < 1e-6:
            return f"{int(round(value))}s"
        return f"{value:.1f}".rstrip("0").rstrip(".") + "s"
    denom = int(round(1 / value))
    if denom < 1:
        return None
    return f"1/{denom}"


def _exif_lookup(exif, nested: dict, tag: int):
    return nested.get(tag) or exif.get(tag)


def _exif_camera_fields(image) -> tuple[str | None, str | None, int | None, str | None, str | None]:
    try:
        exif = image.getexif()
    except Exception:
        return None, None, None, None, None
    if not exif:
        return None, None, None, None, None
    nested: dict = {}
    try:
        nested = dict(exif.get_ifd(_EXIF_IFD) or {})
    except Exception:
        nested = {}
    camera = _format_camera(_exif_lookup(exif, nested, _EXIF_MAKE), _exif_lookup(exif, nested, _EXIF_MODEL))
    lens = _format_lens(
        _exif_lookup(exif, nested, _EXIF_LENS_MAKE),
        _exif_lookup(exif, nested, _EXIF_LENS_MODEL),
    )
    iso = _exif_iso(_exif_lookup(exif, nested, _EXIF_ISO) or _exif_lookup(exif, nested, _EXIF_ISO_SENSITIVITY))
    aperture = _format_aperture(_exif_lookup(exif, nested, _EXIF_FNUMBER))
    shutter = _format_shutter(_exif_lookup(exif, nested, _EXIF_EXPOSURE))
    return camera, lens, iso, aperture, shutter


def _exif_gps(image) -> tuple[float | None, float | None]:
    try:
        exif = image.getexif()
        gps = exif.get_ifd(_EXIF_GPS_IFD) if exif else None
    except Exception:
        return None, None
    if not gps:
        return None, None
    try:
        lat = _gps_coord(gps.get(2), gps.get(1))
        lng = _gps_coord(gps.get(4), gps.get(3))
    except Exception:
        return None, None
    return lat, lng


def probe_image(path: Path) -> ProbeFields:
    """Pillow 读宽高、EXIF 拍摄时间/GPS/机身光圈等。失败不抛。"""
    register_optional_image_decoders()
    try:
        from PIL import Image, ImageOps
    except ImportError:
        logger.warning("未安装 Pillow，跳过图片探测")
        return ProbeFields()
    try:
        with Image.open(path) as image:
            taken = _exif_taken_at(image)
            lat, lng = _exif_gps(image)
            camera, lens, iso, aperture, shutter = _exif_camera_fields(image)
            oriented = ImageOps.exif_transpose(image)
            width, height = oriented.size
        return ProbeFields(
            width=width,
            height=height,
            exif_taken_at=taken,
            exif_lat=lat,
            exif_lng=lng,
            exif_camera=camera,
            exif_lens=lens,
            exif_iso=iso,
            exif_aperture=aperture,
            exif_shutter=shutter,
        )
    except Exception as exc:
        logger.warning("图片探测失败 %s: %s", path, exc)
        return ProbeFields()


def _video_taken_at(raw: str | None) -> str | None:
    """ffprobe creation_time（可能为 UTC）转成 YYYY-MM-DDTHH:MM:SS。"""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone()
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return normalize_taken_at(text)


def _parse_iso6709(raw: str | None) -> tuple[float | None, float | None]:
    """Parse ISO 6709 / QuickTime location tags into WGS84 lat/lng."""
    if not isinstance(raw, str) or not raw.strip():
        return None, None
    text = raw.strip()
    match = re.search(r"([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)", text)
    if match is None:
        parts = text.split(",")
        if len(parts) < 2:
            return None, None
        try:
            lat, lng = float(parts[0]), float(parts[1])
        except ValueError:
            return None, None
    else:
        lat, lng = float(match.group(1)), float(match.group(2))
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None, None
    if lat == 0 and lng == 0:
        return None, None
    return lat, lng


def _video_gps(tags: dict) -> tuple[float | None, float | None]:
    keys = (
        "location",
        "location-eng",
        "com.apple.quicktime.location.iso6709",
        "gpsposition",
        "xyz",
    )
    normalized = {str(key).lower(): value for key, value in tags.items()}
    for key in keys:
        lat, lng = _parse_iso6709(normalized.get(key))
        if lat is not None and lng is not None:
            return lat, lng
    return None, None


def probe_video(path: Path, *, ffprobe_bin: str | None = None) -> ProbeFields:
    """调用 ffprobe；找不到命令或失败则空。"""
    binary = ffprobe_bin or os.environ.get("FFPROBE_BIN") or shutil.which(FFPROBE_BIN)
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
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None) or {}
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
    format_tags = fmt.get("tags") if isinstance(fmt.get("tags"), dict) else {}
    stream_tags = video.get("tags") if isinstance(video.get("tags"), dict) else {}
    tags = {**stream_tags, **format_tags}
    taken_at = _video_taken_at(tags.get("creation_time"))
    lat, lng = _video_gps(tags)
    audio_tags = audio.get("tags") if isinstance(audio.get("tags"), dict) else {}
    audio_language = audio_tags.get("language")
    audio_channels = audio.get("channels")
    return ProbeFields(
        width=int(width) if isinstance(width, int) else None,
        height=int(height) if isinstance(height, int) else None,
        duration=duration,
        fps=fps,
        bitrate=bitrate,
        codec=str(codec) if codec else None,
        audio_codec=str(audio["codec_name"]) if audio.get("codec_name") else None,
        audio_channels=audio_channels if isinstance(audio_channels, int) else None,
        audio_language=str(audio_language) if audio_language else None,
        exif_taken_at=taken_at,
        exif_lat=lat,
        exif_lng=lng,
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
