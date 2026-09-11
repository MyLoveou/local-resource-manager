"""字幕入库文件名：原始视频 stem + 可选语言后缀。"""

from __future__ import annotations

import re
from pathlib import Path

from app.shared.media_types import SUBTITLE_EXTENSIONS, SUBTITLE_LANGUAGE_TAGS

_UNSAFE = re.compile(r'[\\/:*?"<>|]+')



def sanitize_stem(raw: str) -> str:
    """去掉路径非法字符；空则回退 primary。"""
    cleaned = _UNSAFE.sub("_", raw).strip(" .")
    return cleaned or "primary"


def original_stem_from_extra(extra: dict, title: str) -> str:
    """优先导入源路径的文件名（不含扩展名）。"""
    source = extra.get("importSourcePath")
    if isinstance(source, str) and source.strip():
        return sanitize_stem(Path(source).stem)
    return sanitize_stem(title)


def language_tag(filename: str) -> str | None:
    """从字幕文件名末段取白名单语言；`电影.2020.srt` 不算语言。"""
    stem = Path(filename).stem
    if "." not in stem:
        return None
    tail = stem.rsplit(".", 1)[-1].lower().replace("_", "-")
    if tail in SUBTITLE_LANGUAGE_TAGS:
        return tail
    return None


def subtitle_dest_name(original_stem: str, source_name: str) -> str:
    """`{stem}[.{lang}]{ext}`。"""
    ext = Path(source_name).suffix.lower()
    if ext not in SUBTITLE_EXTENSIONS:
        raise ValueError("invalid subtitle extension")
    lang = language_tag(source_name)
    stem = sanitize_stem(original_stem)
    if lang:
        return f"{stem}.{lang}{ext}"
    return f"{stem}{ext}"
