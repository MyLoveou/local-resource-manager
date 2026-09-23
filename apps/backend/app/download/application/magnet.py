"""校验磁力链接。只保留 xt / dn / 公网 tracker，拒绝可指向内网的直链参数。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from app.download.application.engine import is_video_name, safe_filename
from app.download.application.errors import DownloadError
from app.download.application.ssrf import require_public_host

_HEX = re.compile(r"^[0-9a-fA-F]{40}$")
_BASE32 = re.compile(r"^[2-7A-Z]{32}$")
_ALLOWED = {"xt", "dn", "tr"}
_DIRECT = {"ws", "as", "xs"}


@dataclass(frozen=True)
class MagnetLink:
    canonical: str
    display_name: str | None


def validate_magnet(raw: str) -> MagnetLink:
    text = (raw or "").strip()
    parsed = urlparse(text)
    if parsed.scheme.lower() != "magnet" or not parsed.query:
        raise DownloadError("磁力链接无效", 400)
    params = parse_qs(parsed.query, keep_blank_values=False)
    lowered = {key.lower() for key in params}
    if lowered & _DIRECT:
        raise DownloadError("磁力链接不能带直链参数", 400)
    extra = lowered - _ALLOWED
    if extra:
        raise DownloadError("磁力链接包含不支持的参数", 400)
    xt_values = [value for key, values in params.items() if key.lower() == "xt" for value in values]
    if len(xt_values) != 1 or not xt_values[0].lower().startswith("urn:btih:"):
        raise DownloadError("仅支持 BT 磁力", 400)
    infohash = xt_values[0].split(":", 2)[-1].strip()
    if _HEX.fullmatch(infohash):
        infohash = infohash.lower()
    elif _BASE32.fullmatch(infohash.upper()):
        infohash = infohash.upper()
    else:
        raise DownloadError("磁力哈希无效", 400)

    display: str | None = None
    for key, values in params.items():
        if key.lower() == "dn" and values and values[0].strip():
            display = safe_filename(unquote(values[0].strip()))
            break
    trackers: list[str] = []
    for key, values in params.items():
        if key.lower() != "tr":
            continue
        for value in values:
            trackers.append(_validate_tracker(value))

    parts = [f"xt=urn:btih:{infohash}"]
    if display:
        parts.append(f"dn={quote(display)}")
    for tracker in trackers:
        parts.append(f"tr={quote(tracker, safe='')}")
    return MagnetLink("magnet:?" + "&".join(parts), display)


def pick_video(dest: Path, reported: list[Path]) -> Path:
    candidates: list[Path] = []
    seen: set[Path] = set()
    for path in reported:
        resolved = path if path.is_absolute() else dest / path
        if resolved in seen or not resolved.is_file() or not is_video_name(resolved.name):
            continue
        seen.add(resolved)
        candidates.append(resolved)
    if dest.is_dir():
        for path in dest.rglob("*"):
            if path in seen or not path.is_file() or not is_video_name(path.name):
                continue
            seen.add(path)
            candidates.append(path)
    if not candidates:
        raise DownloadError("没有可入库的视频", 400)
    return max(candidates, key=lambda item: item.stat().st_size)


def _validate_tracker(raw: str) -> str:
    text = raw.strip()
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https", "udp"}:
        raise DownloadError("磁力 tracker 无效", 400)
    host = (parsed.hostname or "").strip().rstrip(".")
    if not host:
        raise DownloadError("磁力 tracker 无效", 400)
    require_public_host(host)
    return text
