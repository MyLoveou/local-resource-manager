"""导入前预览：先算出会被建出来的结构，确认后再落盘。

与真正的导入共用同一套规划逻辑（AI 判定特典 + 规则编号 + 标题清洗），
所以预览看到的就是导入会得到的结果。模型温度固定为 0，重复调用结论稳定。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

VIDEO_SUFFIXES = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".ts",
    ".m2ts",
    ".wmv",
    ".flv",
    ".webm",
    ".rmvb",
}


@dataclass(frozen=True)
class PreviewEpisode:
    season: int
    episode: int
    title: str | None
    file: str


@dataclass(frozen=True)
class PreviewExtra:
    title: str
    file: str


@dataclass(frozen=True)
class PreviewSummary:
    seasons: dict[int, list[PreviewEpisode]]
    extras: list[PreviewExtra]
    total_files: int


def collect_videos(root: Path) -> list[Path]:
    """递归收集目录下的视频文件（忽略隐藏文件）。"""
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        if path.name.startswith("."):
            continue
        found.append(path)
    return sorted(found)


def summarize(items: list) -> PreviewSummary:
    """把计划条目整理成「季 → 集」+ 特典。"""
    seasons: dict[int, list[PreviewEpisode]] = {}
    extras: list[PreviewExtra] = []
    for item in items:
        name = Path(str(item.src)).name
        if getattr(item, "kind", None) == "episode" and item.episode is not None:
            seasons.setdefault(int(item.season), []).append(
                PreviewEpisode(
                    season=int(item.season),
                    episode=int(item.episode),
                    title=item.title,
                    file=name,
                )
            )
        else:
            extras.append(PreviewExtra(title=item.title or name, file=name))
    for episodes in seasons.values():
        episodes.sort(key=lambda entry: entry.episode)
    extras.sort(key=lambda entry: entry.title)
    return PreviewSummary(
        seasons={key: seasons[key] for key in sorted(seasons)},
        extras=extras,
        total_files=len(items),
    )
