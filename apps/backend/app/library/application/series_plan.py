"""番剧/AV 目录自动分组。无法识别则返回 None，整夹不入库。

文件名按 Anitomy 思路切 token：方括号里的独立数字是集号，关键字是特典；
不针对某一家字幕组写死整条文件名。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.library.domain.media_types import (
    SERIES_EXTRA_DIR_MARKERS,
    SERIES_EXTRA_TOKEN_PREFIXES,
    SERIES_EXTRA_TOKENS,
)

Kind = Literal["episode", "extra"]

_SEASON_DIR = re.compile(
    r"^(?:season[\s._-]*(\d+)|s(\d{1,2})|第\s*(\d+)\s*季)$",
    re.IGNORECASE,
)
_SXXEXX = re.compile(r"(?i)S(\d{1,2})E(\d{1,3})")
_EXTRA_INLINE = re.compile(
    r"(?i)(?:^|[\s._\-\[(])(?:NCED|NCOP|OVA|OAD|SPECIAL|EXTRA|特典|(?:SP|MENU|PV|CM|NC)\d*)(?:$|[\s._\-\[(\])])"
)
_E = re.compile(r"(?i)(?:^|[\s._\-\[(])(?:E|EP|Episode)[\s._-]?(\d{1,3})(?=$|[\s._\-\])])")
_DASH = re.compile(r"\s-\s(\d{1,3})(?:\s|\.|\[|$)")
_ZH = re.compile(r"第(\d{1,3})[话話集回]")
_LEAD = re.compile(r"^(\d{1,3})(?:[\s._-]|$)")
_PURE_EP = re.compile(r"^\d{1,3}$")
_TOKEN_SPLIT = re.compile(r"[\[\]()]+")
_DIR_SPLIT = re.compile(r"[&+,]+")


@dataclass(frozen=True)
class PlannedItem:
    """一条待复制的集或特典。"""

    src: Path
    kind: Kind
    season: int
    episode: int | None
    dest_rel: str
    title: str | None


_DETAIL_CAP = 20
_FAIL_MESSAGES = {
    "no_videos": "目录里没有可识别的视频文件",
    "mixed_season_dirs": "部分正片在季目录（Season/Sxx）里，部分不在，无法自动对齐",
    "unrecognized_names": "无法从文件名识别集号（需要 Season 目录、SxxExx 或可解析序号）",
    "missing_episode": "已按目录或文件名布局识别，仍有文件抽不出集号",
    "duplicate_episode": "多个文件落到同一季集号",
}


@dataclass(frozen=True)
class ExplainedPlan:
    """系列目录识别结果：成功含计划，失败含 code 与文件说明。"""

    ok: bool
    items: tuple[PlannedItem, ...] = ()
    code: str | None = None
    message: str = ""
    details: tuple[str, ...] = ()


def _cap_details(lines: list[str]) -> tuple[str, ...]:
    if len(lines) <= _DETAIL_CAP:
        return tuple(lines)
    kept = _DETAIL_CAP - 1
    omitted = len(lines) - kept
    return tuple(lines[:kept] + [f"另有 {omitted} 个文件未列出"])


def _fail(code: str, details: list[str]) -> ExplainedPlan:
    return ExplainedPlan(False, (), code, _FAIL_MESSAGES[code], _cap_details(details))


def _ok(items: list[PlannedItem], auto_numbered: int = 0) -> ExplainedPlan:
    episodes = [item for item in items if item.kind == "episode"]
    extras = [item for item in items if item.kind == "extra"]
    seasons = {item.season for item in episodes}
    message = f"已识别 {len(seasons)} 季 · {len(episodes)} 集 · {len(extras)} 特典"
    if auto_numbered:
        message += f"（{auto_numbered} 集按文件名顺序自动编号）"
    details: list[str] = []
    for item in items:
        if item.kind == "episode" and item.episode is not None:
            details.append(f"S{item.season:02d}E{item.episode:02d} ← {item.src.name}")
        else:
            details.append(f"特典 ← {item.src.name}")
    return ExplainedPlan(True, tuple(items), None, message, _cap_details(details))


def _int_group(match: re.Match[str]) -> int:
    for value in match.groups():
        if value is not None:
            return int(value)
    raise ValueError("empty season match")


def season_from_dir_name(name: str) -> int | None:
    """Season 01 / S01 / 第1季。"""
    match = _SEASON_DIR.match(name.strip())
    if match is None:
        return None
    return _int_group(match)


def _season_in_path(root: Path, src: Path) -> int | None:
    try:
        relative = src.parent.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    for part in relative.parts:
        number = season_from_dir_name(part)
        if number is not None:
            return number
    return None


def filename_tokens(stem: str) -> list[str]:
    """去掉 []() 后的片段，对应 Anitomy 的 bracket token。"""
    return [piece.strip() for piece in _TOKEN_SPLIT.split(stem) if piece.strip()]


def _token_is_extra(token: str) -> bool:
    lowered = token.strip().lower()
    if lowered in SERIES_EXTRA_TOKENS:
        return True
    for prefix in SERIES_EXTRA_TOKEN_PREFIXES:
        rest = lowered[len(prefix) :] if lowered.startswith(prefix) else None
        if rest is None:
            continue
        if rest == "" or rest.isdigit():
            return True
    return False


def _dir_is_extra(part: str) -> bool:
    lowered = part.strip().lower()
    if lowered in SERIES_EXTRA_DIR_MARKERS or "特典" in part:
        return True
    for piece in _DIR_SPLIT.split(lowered):
        piece = piece.strip()
        if piece in SERIES_EXTRA_DIR_MARKERS:
            return True
    return False


def _is_extra(root: Path, path: Path) -> bool:
    """目录关键字或文件名 token 命中特典表。"""
    if _SXXEXX.search(path.stem):
        return False
    if _EXTRA_INLINE.search(path.stem):
        return True
    if any(_token_is_extra(token) for token in filename_tokens(path.stem)):
        return True
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return any(_dir_is_extra(part) for part in relative.parts[:-1])


def _episode_from_tokens(stem: str) -> int | None:
    """独立数字 token，如 [01]；1080P 不是纯数字故不会误伤。"""
    for token in filename_tokens(stem):
        if _PURE_EP.fullmatch(token):
            number = int(token)
            if 1 <= number <= 999:
                return number
    return None


def episode_number_from_stem(stem: str) -> int | None:
    match = _SXXEXX.search(stem)
    if match:
        return int(match.group(2))
    for pattern in (_E, _DASH, _ZH, _LEAD):
        match = pattern.search(stem)
        if match:
            return int(match.group(1))
    return _episode_from_tokens(stem)


def sxx_season_from_stem(stem: str) -> int | None:
    match = _SXXEXX.search(stem)
    return int(match.group(1)) if match else None


def explain_series_plan(root: Path, videos: list[Path]) -> ExplainedPlan:
    """识别成功或带原因失败。ingest 只走此入口。"""
    if not videos:
        return _fail("no_videos", [])
    extras: list[Path] = []
    episodes: list[Path] = []
    for path in videos:
        if _is_extra(root, path):
            extras.append(path)
        else:
            episodes.append(path)
    if not episodes and not extras:
        return _fail("no_videos", [path.name for path in videos])

    in_season = [path for path in episodes if _season_in_path(root, path) is not None]
    out_season = [path for path in episodes if _season_in_path(root, path) is None]
    if in_season and out_season:
        return _fail("mixed_season_dirs", [path.name for path in out_season])

    if in_season:
        mode = "dir"
    elif episodes and all(sxx_season_from_stem(path.stem) is not None for path in episodes):
        mode = "sxx"
    elif episodes and all(episode_number_from_stem(path.stem) is not None for path in episodes):
        mode = "flat"
    elif not episodes and extras:
        mode = "extras"
    elif episodes and not any(
        episode_number_from_stem(path.stem) is not None or sxx_season_from_stem(path.stem) is not None
        for path in episodes
    ):
        # L3 降级：完全抽不出集号 → 按文件名顺序自动编号，仍可入库
        mode = "numbered"
    elif episodes:
        # 混合：识别出的照用，抽不出的顺延自动编号
        mode = "flat"
    else:
        unnamed = [
            path.name
            for path in episodes
            if episode_number_from_stem(path.stem) is None and sxx_season_from_stem(path.stem) is None
        ]
        return _fail("unrecognized_names", unnamed or [path.name for path in episodes])

    items: list[PlannedItem] = []
    seen: dict[tuple[int, int], str] = {}
    auto_numbered = 0
    next_by_season: dict[int, int] = {}
    duplicates: list[str] = []
    for path in sorted(episodes, key=lambda item: item.as_posix().lower()):
        if mode == "dir":
            season = _season_in_path(root, path)
            episode = episode_number_from_stem(path.stem)
        elif mode == "sxx":
            season = sxx_season_from_stem(path.stem)
            episode = episode_number_from_stem(path.stem)
        elif mode == "numbered":
            season = 1
            episode = None
        else:
            season = sxx_season_from_stem(path.stem) or 1
            episode = episode_number_from_stem(path.stem)
        if season is None:
            continue
        if episode is None:
            # 抽不出集号的：在该季已识别最大集号之后按文件名顺序顺延编号
            start = next_by_season.get(season)
            if start is None:
                recognized_max = max((ep for (s, ep) in seen if s == season), default=0)
                start = recognized_max + 1
                next_by_season[season] = start
            episode = next_by_season[season]
            next_by_season[season] = episode + 1
            auto_numbered += 1
        key = (season, episode)
        previous = seen.get(key)
        if previous is not None:
            duplicates.append(f"{path.name} 与 {previous} 均为 S{season:02d}E{episode:02d}")
            continue
        seen[key] = path.name
        dest = f"seasons/{season:02d}/S{season:02d}E{episode:02d}{path.suffix.lower()}"
        items.append(PlannedItem(path, "episode", season, episode, dest, None))
    if duplicates:
        return _fail("duplicate_episode", duplicates)

    used_names: set[str] = set()
    for index, path in enumerate(sorted(extras, key=lambda item: item.name.lower())):
        name = path.name
        if name.lower() in used_names:
            name = f"{path.stem}_{index}{path.suffix.lower()}"
        used_names.add(name.lower())
        items.append(PlannedItem(path, "extra", 0, None, f"extras/{name}", _extra_title(path)))
    return _ok(items, auto_numbered)


def _extra_title(path: Path) -> str:
    """特典标题：剥掉发布组/分辨率/编码等，但保留 PV、特典标记与番号。"""
    from app.library.application.smart_import.title_clean import clean_release_name

    cleaned = clean_release_name(path.stem).title
    return cleaned or path.stem


def plan_series_videos(root: Path, videos: list[Path]) -> list[PlannedItem] | None:
    """全部可自动识别才返回计划；否则 None。"""
    explained = explain_series_plan(root, videos)
    return list(explained.items) if explained.ok else None


def classify_single_video(root: Path, path: Path) -> tuple[str, int, int | None, str | None]:
    """单文件分类（监视增量入库用）：(kind, season, episode, title)。

    抽不出集号的视频归特典（title=文件名），保证任何渠道的文件都能进库。
    """
    if _is_extra(root, path):
        return ("extra", 0, None, _extra_title(path))
    season = _season_in_path(root, path)
    if season is None:
        season = sxx_season_from_stem(path.stem)
    episode = episode_number_from_stem(path.stem)
    if episode is None:
        return ("extra", 0, None, path.stem)
    return ("episode", season or 1, episode, None)
