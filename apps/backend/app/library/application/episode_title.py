"""每集标题：从文件名里抠出「集号之后的标题」。

大多数发布组命名里，集号之后的文字就是这一集的标题，例如
`[Group] Show - 03 孤独的转校生 [1080p].mkv` 的标题是「孤独的转校生」。
抽不出有意义的内容时返回 None——**不要**把作品名当成每集标题。
"""

from __future__ import annotations

import re
from pathlib import Path

from app.library.application.smart_import.title_clean import clean_release_name

MAX_TITLE = 80

_BRACKETS = re.compile(r"\[[^\]]*\]|\([^)]*\)|【[^】]*】|「[^」]*」")
_EPISODE_MARK = re.compile(
    r"(?:^|[\s._\-])"
    r"(?:s\d{1,2}\s*e\d{1,4}|第\s*\d{1,4}\s*[话話集]|(?:ep|episode|e)\s*\d{1,4}|\d{1,4}(?:\s*[话話集])?)"
    r"(?=$|[\s._\-\]\[(（])",
    re.IGNORECASE,
)
_NOISE = re.compile(
    r"\b(?:1080p|720p|2160p|4k|bluray|bdrip|webrip|web-dl|hdtv|hevc|x264|x265|avc|"
    r"aac|flac|opus|ma10p|10bit|8bit|ncop|nced|chs|cht|jpn|eng)\b",
    re.IGNORECASE,
)
_SEASON = re.compile(r"\b(?:s\d{1,2}|season\s*\d{1,2}|第\s*\d{1,2}\s*季)\b", re.IGNORECASE)
_SEPARATORS = re.compile(r"[\s\-_.·:：]+")


def _normalize(text: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text.lower())


def episode_title_from_stem(stem: str, series_title: str | None = None) -> str | None:
    """从文件名解析集标题；没有可用信息返回 None。"""
    plain = _BRACKETS.sub(" ", Path(stem).stem if Path(stem).suffix else stem)
    mark = _EPISODE_MARK.search(plain)
    tail = plain[mark.end() :] if mark else ""
    tail = _NOISE.sub(" ", tail)
    tail = _SEASON.sub(" ", tail)
    candidate = _SEPARATORS.sub(" ", tail).strip(" -_.·:：")
    if not candidate:
        return None
    candidate = candidate[:MAX_TITLE].strip()

    # 只剩作品名（或作品名的一部分）时不算标题
    title_key = _normalize(series_title or "")
    if title_key and _normalize(candidate) in {title_key, ""}:
        return None
    if title_key and _normalize(candidate).startswith(title_key) and len(
        _normalize(candidate)
    ) <= len(title_key) + 2:
        return None

    # 太短或只剩数字/符号的，不要
    if len(_normalize(candidate)) < 2 or candidate.isdigit():
        return None
    # 纯中文标题至少两个字，纯英文至少三个字母
    if re.fullmatch(r"[\u4e00-\u9fff]{1}", candidate):
        return None
    return candidate


def series_title_for(stem: str) -> str | None:
    """辅助：用规则清洗出的作品名，供上面的比较使用。"""
    cleaned = clean_release_name(stem).title.strip()
    return cleaned or None
