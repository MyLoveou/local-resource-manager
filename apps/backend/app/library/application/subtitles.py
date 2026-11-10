"""字幕发现与匹配（纯逻辑为主，便于单测）。

三条原则（需求 IN 3）：
1. 集号相同优先——最可靠
2. 无集号时按文件主干相似度兜底
3. 都不中就不挂——错挂比不挂更难发现
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

SUBTITLE_SUFFIXES = frozenset({".srt", ".vtt", ".ass", ".ssa"})

# `<track>` 只能播 vtt；srt 由前端转换
RENDERABLE_SUFFIXES = frozenset({".srt", ".vtt"})

SUBTITLE_DIR_HINTS = ("subs", "sub", "字幕", "subtitles", "subtitle")

SIMILARITY_THRESHOLD = 0.8

_BRACKET = re.compile(r"[\[\(（【][^\[\]\(\)（）【】]*[\]\)）】]")
_EPISODE = re.compile(r"(?:^|[\s._\-\[(])(?:第\s*)?(\d{1,4})(?:\s*[话集])?(?=$|[\s._\-\])])")
_NON_WORD = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")

_LANGUAGE_RULES: tuple[tuple[str, str], ...] = (
    ("简繁", "zh-Hans/zh-Hant"),
    ("简日", "zh-Hans/ja"),
    ("繁日", "zh-Hant/ja"),
    ("双语", "zh/ja"),
    ("简体", "zh-Hans"),
    ("繁体", "zh-Hant"),
    ("简中", "zh-Hans"),
    ("繁中", "zh-Hant"),
    ("chs", "zh-Hans"),
    ("cht", "zh-Hant"),
    ("sc", "zh-Hans"),
    ("tc", "zh-Hant"),
    ("jpn", "ja"),
    ("jp", "ja"),
    ("eng", "en"),
)


def is_subtitle(path: Path) -> bool:
    return path.suffix.lower() in SUBTITLE_SUFFIXES


def is_renderable(path: Path) -> bool:
    """浏览器 <track> 能直接用的格式（ass/ssa 需要原生渲染，本版不支持）。"""
    return path.suffix.lower() in RENDERABLE_SUFFIXES


def infer_language(name: str) -> str | None:
    lowered = name.lower()
    for marker, language in _LANGUAGE_RULES:
        if marker in lowered:
            return language
    return None


def strip_brackets(text: str) -> str:
    return _BRACKET.sub(" ", text)


def episode_number(name: str) -> int | None:
    """从文件名取集号；取最后一个独立数字段。

    注意：集号通常就在方括号里（`[03]`），所以**不能先剥括号**。
    `1080P`、`10bit` 这类会因为数字后面紧跟字母而落选。
    """
    stem = Path(name).stem
    found = _EPISODE.findall(stem)
    if not found:
        return None
    try:
        return int(found[-1])
    except ValueError:
        return None


def _normalized(name: str) -> str:
    stem = strip_brackets(Path(name).stem)
    stem = _EPISODE.sub(" ", stem)
    return _NON_WORD.sub("", stem).lower()


def similarity(left: str, right: str) -> float:
    a, b = _normalized(left), _normalized(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def discover_subtitles(root: Path) -> list[Path]:
    """扫描根目录与常见字幕子目录下的字幕文件。"""
    if not root.exists():
        return []
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or not is_subtitle(path):
            continue
        relative = path.relative_to(root)
        in_subtitle_dir = any(
            part.lower() in SUBTITLE_DIR_HINTS or "字幕" in part for part in relative.parts[:-1]
        )
        if len(relative.parts) == 1 or in_subtitle_dir:
            found.append(path)
    return sorted(found)


def match_subtitle(video: Path, candidates: list[Path]) -> Path | None:
    """给一个视频找最合适的字幕；宁缺勿错。"""
    if not candidates:
        return None

    number = episode_number(video.name)
    if number is not None:
        same = [item for item in candidates if episode_number(item.name) == number]
        if len(same) == 1:
            return same[0]
        if len(same) > 1:
            # 同集多语言时取相似度最高的一条
            return max(same, key=lambda item: similarity(video.name, item.name))

    scored = sorted(
        ((similarity(video.name, item.name), item) for item in candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    if scored and scored[0][0] >= SIMILARITY_THRESHOLD:
        return scored[0][1]
    return None


def match_all(videos: list[Path], candidates: list[Path]) -> dict[Path, list[Path]]:
    """为每个视频找字幕；同一视频可有多条（多语言）。

    只在相似度或集号命中时挂载，未命中的视频不在返回值里。
    """
    result: dict[Path, list[Path]] = {}
    for video in videos:
        number = episode_number(video.name)
        matched: list[Path] = []
        for candidate in candidates:
            candidate_number = episode_number(candidate.name)
            if number is not None and candidate_number is not None:
                if candidate_number == number:
                    matched.append(candidate)
                continue
            if similarity(video.name, candidate.name) >= SIMILARITY_THRESHOLD:
                matched.append(candidate)
        if matched:
            result[video] = matched
    return result
