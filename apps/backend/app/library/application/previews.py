"""Create a browser-friendly preview for formats Chromium cannot decode."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from app.shared.image_support import register_optional_image_decoders
from app.shared.log import logger

PREVIEW_MAX_EDGE_PX = 2048
PREVIEW_JPEG_QUALITY = 88


def write_preview(source: Path, dest: Path) -> Path | None:
    """Write a JPEG preview; keep the original file untouched."""
    register_optional_image_decoders()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()
            frame = image.convert("RGB")
            frame.thumbnail((PREVIEW_MAX_EDGE_PX, PREVIEW_MAX_EDGE_PX), Image.Resampling.LANCZOS)
            frame.save(tmp, format="JPEG", quality=PREVIEW_JPEG_QUALITY, optimize=True)
        tmp.replace(dest)
        return dest
    except Exception as exc:  # noqa: BLE001 - preview failure must not break import
        logger.warning("预览图生成失败 %s: %s", source, exc)
        tmp.unlink(missing_ok=True)
        return None
