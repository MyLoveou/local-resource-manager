"""从 PE 抽出最大图标栅格为 PNG。失败返回 False。"""

from __future__ import annotations

import io
import struct
from pathlib import Path

from app.shared.log import logger

_RT_ICON = 3
_RT_GROUP_ICON = 14


def extract_exe_icon(exe: Path, dest_png: Path) -> bool:
    try:
        import pefile
        from PIL import Image
    except ImportError as exc:
        logger.warning("抽 exe 图标缺少依赖: %s", exc)
        return False
    try:
        pe = pefile.PE(str(exe), fast_load=True)
        try:
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
            )
            ico = _best_ico(pe)
        finally:
            pe.close()
        if not ico:
            return False
        dest_png.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest_png.with_name(dest_png.name + ".tmp")
        with Image.open(io.BytesIO(ico)) as image:
            image.load()
            frame = image.convert("RGBA")
            frame.save(tmp, format="PNG")
        tmp.replace(dest_png)
        return dest_png.is_file() and dest_png.stat().st_size > 0
    except Exception as exc:
        logger.warning("抽 exe 图标失败 %s: %s", exe, exc)
        return False


def _best_ico(pe) -> bytes | None:
    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        return None
    icons: dict[int, bytes] = {}
    groups: list[bytes] = []
    for entry_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry_type.id == _RT_ICON and hasattr(entry_type, "directory"):
            for entry_id in entry_type.directory.entries:
                if not hasattr(entry_id, "directory"):
                    continue
                for entry_lang in entry_id.directory.entries:
                    data = pe.get_data(
                        entry_lang.data.struct.OffsetToData, entry_lang.data.struct.Size
                    )
                    icons[int(entry_id.id)] = data
        if entry_type.id == _RT_GROUP_ICON and hasattr(entry_type, "directory"):
            for entry_id in entry_type.directory.entries:
                if not hasattr(entry_id, "directory"):
                    continue
                for entry_lang in entry_id.directory.entries:
                    groups.append(
                        pe.get_data(
                            entry_lang.data.struct.OffsetToData, entry_lang.data.struct.Size
                        )
                    )
    if not groups or not icons:
        if icons:
            largest = max(icons.values(), key=len)
            return _wrap_single_ico(largest)
        return None
    return _assemble_group_ico(groups[0], icons)


def _wrap_single_ico(dib: bytes) -> bytes:
    return _assemble_group_ico(b"\x00\x00\x01\x00\x01\x00" + bytes(12) + b"\x00\x00", {0: dib})


def _assemble_group_ico(grp: bytes, icons: dict[int, bytes]) -> bytes | None:
    if len(grp) < 6:
        return None
    count = struct.unpack_from("<H", grp, 4)[0]
    entries = []
    offset = 6
    for _ in range(count):
        if offset + 14 > len(grp):
            break
        width, height, colors, reserved, planes, bitcount, bytes_in_res, icon_id = struct.unpack_from(
            "<BBBBHHIH", grp, offset
        )
        offset += 14
        blob = icons.get(icon_id)
        if blob is None:
            continue
        entries.append((width, height, colors, reserved, planes, bitcount, blob))
    if not entries:
        return None
    entries.sort(key=lambda item: (item[0] or 256) * (item[1] or 256), reverse=True)
    chosen = entries[:1]
    header = struct.pack("<HHH", 0, 1, len(chosen))
    data = b""
    dir_size = 6 + 16 * len(chosen)
    cursor = dir_size
    dirs = b""
    for width, height, colors, reserved, planes, bitcount, blob in chosen:
        dirs += struct.pack(
            "<BBBBHHII",
            width,
            height,
            colors,
            reserved,
            planes,
            bitcount,
            len(blob),
            cursor,
        )
        data += blob
        cursor += len(blob)
    return header + dirs + data
