"""音轨枚举与按轨 remux。

`<video>` 只能播容器默认音轨，切换音轨必须由后端用 ffmpeg 抽出一条：
`-map 0:v:0 -map 0:a:N -c copy`（只 remux，不转码）。

不做数据库迁移：音轨信息在播放时用 ffprobe 现查，几毫秒，且永远与文件一致。
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import time
from pathlib import Path

from app.library.domain.media_types import FFMPEG_BIN, FFPROBE_BIN, FFPROBE_TIMEOUT_SEC
from app.shared.log import logger

_REMUX_TIMEOUT_SEC = 600
_CACHE_TTL_SEC = 7 * 24 * 3600

_LANGUAGE_NAMES = {
    "jpn": "日语",
    "ja": "日语",
    "chi": "中文",
    "zho": "中文",
    "zh": "中文",
    "eng": "英语",
    "en": "英语",
}


def _binary(name: str) -> str | None:
    return shutil.which(name)


def list_audio_tracks(path: Path) -> list[dict]:
    """返回 [{index, streamIndex, language, codec, channels, title, label}]。"""
    binary = _binary(FFPROBE_BIN)
    if binary is None or not path.is_file():
        return []
    try:
        completed = subprocess.run(
            [
                binary,
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            timeout=FFPROBE_TIMEOUT_SEC,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("音轨探测失败 %s: %s", path, exc)
        return []
    if completed.returncode != 0:
        return []
    try:
        payload = json.loads(completed.stdout.decode("utf-8", errors="replace") or "{}")
    except json.JSONDecodeError:
        return []

    tracks: list[dict] = []
    for position, stream in enumerate(payload.get("streams") or []):
        tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
        language = str(tags.get("language") or "").strip() or None
        title = str(tags.get("title") or "").strip() or None
        codec = str(stream.get("codec_name") or "").strip() or None
        channels = stream.get("channels")
        label_parts = [
            _LANGUAGE_NAMES.get((language or "").lower(), language or ""),
            title or "",
            codec or "",
        ]
        label = " · ".join([part for part in label_parts if part]) or f"音轨 {position + 1}"
        tracks.append(
            {
                "index": position,
                "streamIndex": stream.get("index"),
                "language": language,
                "codec": codec,
                "channels": int(channels) if isinstance(channels, int) else None,
                "title": title,
                "label": label,
            }
        )
    return tracks


def cache_dir(base: Path) -> Path:
    target = base / "cache" / "audio"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _prune(directory: Path) -> None:
    deadline = time.time() - _CACHE_TTL_SEC
    for entry in directory.glob("*.mkv"):
        try:
            if entry.stat().st_mtime < deadline:
                entry.unlink(missing_ok=True)
        except OSError:
            continue


def ensure_remuxed(source: Path, index: int, target_dir: Path) -> Path | None:
    """把第 index 条音轨抽成独立文件并缓存；失败返回 None。"""
    binary = _binary(FFMPEG_BIN)
    if binary is None or not source.is_file():
        return None
    directory = cache_dir(target_dir)
    _prune(directory)
    target = directory / f"{source.stem}-a{index}.mkv"
    try:
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            return target
    except OSError:
        pass
    tmp = target.with_suffix(".part.mkv")
    try:
        completed = subprocess.run(
            [
                binary,
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                f"0:a:{index}",
                "-c",
                "copy",
                str(tmp),
            ],
            capture_output=True,
            timeout=_REMUX_TIMEOUT_SEC,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("音轨抽取失败 %s#%s: %s", source, index, exc)
        return None
    if completed.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
        err = completed.stderr.decode("utf-8", errors="replace") if completed.stderr else ""
        logger.warning("音轨抽取失败 %s#%s: %s", source, index, err.strip()[:400])
        tmp.unlink(missing_ok=True)
        return None
    tmp.replace(target)
    return target


async def ensure_remuxed_async(source: Path, index: int, target_dir: Path) -> Path | None:
    return await asyncio.to_thread(ensure_remuxed, source, index, target_dir)
