"""Windows 快捷方式目标路径。非 Win 或解析失败返回 None。"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from app.shared.log import logger

_HEADER = 0x4C
_HAS_ID_LIST = 0x00000001
_HAS_LINK_INFO = 0x00000002
_VOLUME_AND_LOCAL = 0x00000001


def resolve_lnk_target(lnk: Path) -> Path | None:
    if sys.platform != "win32":
        return None
    try:
        data = lnk.read_bytes()
    except OSError as exc:
        logger.warning("读取 lnk 失败 %s: %s", lnk, exc)
        return None
    if len(data) < _HEADER + 4:
        return None
    flags = struct.unpack_from("<I", data, 0x14)[0]
    offset = _HEADER
    if flags & _HAS_ID_LIST:
        if offset + 2 > len(data):
            return None
        id_size = struct.unpack_from("<H", data, offset)[0]
        offset += 2 + id_size
    if not (flags & _HAS_LINK_INFO):
        return None
    if offset + 16 > len(data):
        return None
    info_size = struct.unpack_from("<I", data, offset)[0]
    header_size = struct.unpack_from("<I", data, offset + 4)[0]
    info_flags = struct.unpack_from("<I", data, offset + 8)[0]
    if info_size < 16 or offset + info_size > len(data):
        return None
    if not (info_flags & _VOLUME_AND_LOCAL):
        return None
    local_off = struct.unpack_from("<I", data, offset + 16)[0]
    if header_size >= 0x24:
        local_off_u = struct.unpack_from("<I", data, offset + 0x1C)[0]
        if local_off_u:
            start = offset + local_off_u
            end = data.find(b"\x00\x00", start)
            if end == -1:
                return None
            try:
                text = data[start:end].decode("utf-16-le")
            except UnicodeDecodeError:
                return None
            path = Path(text)
            return path if path.is_file() else None
    start = offset + local_off
    end = data.find(b"\x00", start)
    if end == -1:
        return None
    try:
        text = data[start:end].decode("ascii", errors="strict")
    except UnicodeDecodeError:
        try:
            text = data[start:end].decode("mbcs", errors="replace")
        except LookupError:
            text = data[start:end].decode("latin-1")
    path = Path(text)
    return path if path.is_file() else None
