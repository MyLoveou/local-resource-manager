"""从 cbz（zip）抽出自然序第一张图。"""

from __future__ import annotations

import posixpath
import zipfile
from pathlib import Path

from app.library.application.covers.image_bytes import save_image_bytes_as_jpeg
from app.library.application.ingest.placement import natural_key, skip_entry
from app.library.domain.type_profile import IMAGE_EXTENSIONS
from app.shared.log import logger

_MAX_MEMBER_BYTES = 32 * 1024 * 1024


def extract_cbz_first_image(cbz: Path, dest_jpg: Path) -> bool:
    """zip 内图片扩展名、跳过隐藏，自然序第一张。"""
    try:
        with zipfile.ZipFile(cbz) as archive:
            candidates: list[str] = []
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                base = posixpath.basename(name)
                if skip_entry(base):
                    continue
                if Path(base).suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                candidates.append(name)
            if not candidates:
                return False
            candidates.sort(key=lambda item: natural_key(Path(posixpath.basename(item))))
            chosen = candidates[0]
            info = archive.getinfo(chosen)
            if info.file_size > _MAX_MEMBER_BYTES:
                logger.warning("cbz 封面条目过大 %s", chosen)
                return False
            data = archive.read(chosen)
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        logger.warning("cbz 封面抽取失败 %s: %s", cbz, exc)
        return False
    return save_image_bytes_as_jpeg(data, dest_jpg)
