"""从 EPUB 抽出封面图。失败返回 False。"""

from __future__ import annotations

import posixpath
import zipfile
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from app.library.application.covers.image_bytes import save_image_bytes_as_jpeg
from app.library.application.ingest.placement import skip_entry
from app.library.domain.type_profile import IMAGE_EXTENSIONS
from app.shared.log import logger

_COVER_STEMS = frozenset({"cover", "folder", "poster"})
_CONTAINER = "META-INF/container.xml"
_MAX_MEMBER_BYTES = 32 * 1024 * 1024


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _zip_join(base_dir: str, href: str) -> str:
    cleaned = unquote(href).replace("\\", "/")
    if cleaned.startswith("/"):
        return cleaned.lstrip("/")
    return posixpath.normpath(posixpath.join(base_dir, cleaned))


def _read_member(archive: zipfile.ZipFile, name: str) -> bytes | None:
    try:
        info = archive.getinfo(name)
    except KeyError:
        return None
    if info.file_size > _MAX_MEMBER_BYTES:
        logger.warning("EPUB 封面条目过大 %s", name)
        return None
    return archive.read(name)


def _opf_cover_href(opf_xml: bytes) -> str | None:
    try:
        root = ET.fromstring(opf_xml)
    except ET.ParseError:
        return None
    cover_id: str | None = None
    id_to_href: dict[str, str] = {}
    cover_image_href: str | None = None
    for el in root.iter():
        name = _local(el.tag)
        if name == "meta" and (el.get("name") or "").lower() == "cover":
            cover_id = el.get("content")
        if name == "item":
            item_id = el.get("id")
            href = el.get("href")
            if item_id and href:
                id_to_href[item_id] = href
            props = (el.get("properties") or "").split()
            if "cover-image" in props and href:
                cover_image_href = href
    if cover_image_href:
        return cover_image_href
    if cover_id and cover_id in id_to_href:
        return id_to_href[cover_id]
    return None


def _cover_from_names(names: list[str]) -> str | None:
    images = []
    for name in names:
        if name.endswith("/"):
            continue
        base = posixpath.basename(name)
        if skip_entry(base):
            continue
        path = Path(base)
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if path.stem.lower() in _COVER_STEMS:
            images.append(name)
    return images[0] if images else None


def extract_epub_cover(epub: Path, dest_jpg: Path) -> bool:
    """OPF 封面或 zip 内 cover/folder/poster 图。不用正文第一张插图。"""
    try:
        with zipfile.ZipFile(epub) as archive:
            names = archive.namelist()
            href: str | None = None
            opf_dir = ""
            if _CONTAINER in names:
                raw = _read_member(archive, _CONTAINER)
                container = None
                if raw is not None:
                    try:
                        container = ET.fromstring(raw)
                    except ET.ParseError:
                        container = None
                if container is not None:
                    for el in container.iter():
                        if _local(el.tag) == "rootfile":
                            full = el.get("full-path")
                            if full:
                                opf_path = unquote(full).replace("\\", "/")
                                opf_dir = posixpath.dirname(opf_path)
                                opf_raw = _read_member(archive, opf_path)
                                href = _opf_cover_href(opf_raw) if opf_raw is not None else None
                                break
            zip_name = _zip_join(opf_dir, href) if href else None
            if zip_name is None or zip_name not in names:
                zip_name = _cover_from_names(names)
            if zip_name is None:
                return False
            data = _read_member(archive, zip_name)
            if data is None:
                return False
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        logger.warning("EPUB 封面抽取失败 %s: %s", epub, exc)
        return False
    return save_image_bytes_as_jpeg(data, dest_jpg)
