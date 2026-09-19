"""把任意可读图字节写成 JPEG，供 EPUB/cbz 抽出后 attach。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.shared.log import logger

_MAX_BYTES = 32 * 1024 * 1024


def save_image_bytes_as_jpeg(data: bytes, dest_jpg: Path) -> bool:
    """Pillow 能开则写成 dest JPEG。"""
    if len(data) > _MAX_BYTES:
        logger.warning("封面图字节过大")
        return False
    dest_jpg.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_jpg.with_name(f"{dest_jpg.stem}.part.jpg")
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            frame = image.convert("RGB")
            frame.save(tmp, format="JPEG", quality=90)
        tmp.replace(dest_jpg)
        return dest_jpg.is_file() and dest_jpg.stat().st_size > 0
    except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError, MemoryError) as exc:
        logger.warning("封面图无法解码: %s", exc)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False
