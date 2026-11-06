"""导入前预览：先算出会被建出来的结构，确认后再落盘。

预览得到的计划**会被缓存**，导入时按目录直接取用——不再重新问模型，
所以用户确认的那一份就是实际入库的那一份。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

TTL_SEC = 30 * 60
MAX_PLANS = 10

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


@dataclass
class CachedPlan:
    """预览算好的计划；按根目录缓存，导入时取用一次即作废。"""

    root: str
    items: list
    message: str
    ok: bool
    code: str | None
    details: tuple[str, ...]
    created_at: float = field(default_factory=time.time)


class PlanCache:
    def __init__(self) -> None:
        self._plans: dict[str, CachedPlan] = {}

    def _key(self, root: Path) -> str:
        return str(root.resolve()).lower()

    def _prune(self) -> None:
        deadline = time.time() - TTL_SEC
        for key in [k for k, v in self._plans.items() if v.created_at < deadline]:
            self._plans.pop(key, None)
        while len(self._plans) > MAX_PLANS:
            oldest = min(self._plans, key=lambda k: self._plans[k].created_at)
            self._plans.pop(oldest, None)

    def put(self, root: Path, explained, items: list) -> None:
        self._prune()
        self._plans[self._key(root)] = CachedPlan(
            root=self._key(root),
            items=list(items),
            message=explained.message,
            ok=explained.ok,
            code=explained.code,
            details=tuple(explained.details),
        )

    def take(self, root: Path) -> CachedPlan | None:
        self._prune()
        return self._plans.pop(self._key(root), None)


plan_cache = PlanCache()


async def plan_for_import(service, resources, root: Path, videos: list[Path]):
    """导入入口：预览过就直接用缓存结果，否则现场规划。

    `replace` 只改消息，让任务里能看出「沿用预览」。
    """
    from dataclasses import replace

    cached = plan_cache.take(root)
    if cached is not None:
        return replace(_plan_from_cache(cached), message=f"{cached.message}（沿用预览）")
    return await service.plan_series(resources, root, videos)


def _plan_from_cache(cached: CachedPlan):
    """把缓存条目还原成 ExplainedPlan。"""
    from app.library.application.series_plan import ExplainedPlan

    return ExplainedPlan(
        ok=cached.ok,
        code=cached.code or ("ok" if cached.ok else "unknown"),
        message=cached.message,
        details=cached.details,
        items=tuple(cached.items),
    )