"""AI 主导的系列结构拆分。

为什么不是让模型直接给出季/集：

- 114 个文件的 JSON 会在 `num_predict` 处被截断（实测 `done_reason: length`）；
- 小模型会丢字段：要求 `序号|类型|季|集`，它回 `1|4|4|1`；
- 季/集号其实能从文件名和目录名**确定性**解析出来，让模型猜反而更差。

所以分工是：**模型只判断"哪些文件是特典"（语义判断），编号交给规则**。
分批提问、只回编号列表，输出极短，不会被截断。
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from app.library.application.series_plan import (
    ExplainedPlan,
    PlannedItem,
    _extra_title,
    _ok,
    _season_in_path,
    episode_number_from_stem,
)
from app.shared.log import logger

PROMPT_VERSION = "series-plan-v3"
CHUNK_SIZE = 25

_NUMBERS = re.compile(r"\d{1,4}")

_PROMPT = """下面是一个番剧目录里的一批视频文件（编号: 文件名）：

{files}

请找出其中属于**特典**的文件：OVA、OAD、特别篇、角色歌、NCOP/NCED、预告、菜单等，
不是正片剧集的都算。

只输出这些文件的编号，用英文逗号分隔，例如：2,5,7
如果这批全是正片，只输出：none
不要输出其它文字。
"""


def build_prompt(videos: list[Path]) -> str:
    lines = "\n".join(f"{index + 1}: {video.stem}" for index, video in enumerate(videos))
    return _PROMPT.format(files=lines)


def parse_indices(reply: str, expected: int) -> set[int] | None:
    """解析编号集合；`none` 表示空集，无法识别返回 None。"""
    text = (reply or "").strip().lower()
    if not text:
        return None
    compact = text.replace(" ", "")
    if "none" in compact:
        return set()
    numbers = {int(value) for value in _NUMBERS.findall(text)}
    numbers = {value for value in numbers if 1 <= value <= expected}
    if not numbers:
        return None
    return numbers


def build_plan(root: Path, videos: list[Path], extra_paths: set[str]) -> ExplainedPlan:
    """AI 判定特典后，其余按规则编号。"""
    extras: list[Path] = []
    episodes: list[Path] = []
    for path in videos:
        if path.as_posix() in extra_paths:
            extras.append(path)
        else:
            episodes.append(path)

    items: list[PlannedItem] = []
    seen: dict[tuple[int, int], str] = {}
    next_by_season: dict[int, int] = {}
    any_parsed = any(episode_number_from_stem(path.stem) is not None for path in episodes)
    for path in sorted(episodes, key=lambda item: item.as_posix().lower()):
        season = _season_in_path(root, path) or 1
        episode = episode_number_from_stem(path.stem)
        if episode is None:
            if any_parsed:
                extras.append(path)
                continue
            start = next_by_season.get(season)
            if start is None:
                start = max((ep for (s, ep) in seen if s == season), default=0) + 1
                next_by_season[season] = start
            episode = start
            next_by_season[season] = episode + 1
        key = (season, episode)
        if key in seen:
            # 撞号：模型没把它判成特典，但同一集只能有一个文件
            extras.append(path)
            continue
        seen[key] = path.name
        dest = f"seasons/{season:02d}/S{season:02d}E{episode:02d}{path.suffix.lower()}"
        items.append(PlannedItem(path, "episode", season, episode, dest, None))

    for path in sorted(extras, key=lambda item: item.name.lower()):
        items.append(
            PlannedItem(path, "extra", 0, None, f"extras/{path.name}", _extra_title(path))
        )
    plan = _ok(items, 0)
    return replace(plan, message=f"AI 识别：{plan.message}")


async def plan_with_ai(
    root: Path,
    videos: list[Path],
    *,
    complete=None,
) -> ExplainedPlan | None:
    """模型判定特典；不可用、超时或任一批次无法解析都返回 None。"""
    if len(videos) < 2:
        return None
    from app.ai.infrastructure.text_completion import complete as default_complete

    client = complete or default_complete
    ordered = sorted(videos, key=lambda item: item.as_posix().lower())
    extra_paths: set[str] = set()

    for start in range(0, len(ordered), CHUNK_SIZE):
        chunk = ordered[start : start + CHUNK_SIZE]
        try:
            reply = await client(build_prompt(chunk))
        except Exception as exc:  # noqa: BLE001 - 模型失败不该中断导入
            logger.info("AI 结构识别失败: %s", type(exc).__name__)
            return None
        indices = parse_indices(reply or "", len(chunk))
        if indices is None:
            logger.info(
                "AI 结构未通过校验：批次 %s..%s 的回复无法解析", start + 1, start + len(chunk)
            )
            return None
        for index in indices:
            extra_paths.add(chunk[index - 1].as_posix())

    if not extra_paths:
        logger.info("AI 结构：模型判定这批全部是正片")
    return build_plan(root, videos, extra_paths)
