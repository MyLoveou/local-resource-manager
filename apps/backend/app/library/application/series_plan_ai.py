"""AI 主导的系列结构拆分。

为什么不是让模型直接给出季/集：

- 114 个文件的 JSON 会在 `num_predict` 处被截断（实测 `done_reason: length`）；
- 小模型会丢字段：要求 `序号|类型|季|集`，它回 `1|4|4|1`；
- 季/集号其实能从文件名和目录名**确定性**解析出来，让模型猜反而更差。

所以分工是：**模型只判断"哪些文件是特典"（语义判断），编号交给规则**。
分批提问、只回编号列表，输出极短，不会被截断。
"""

from __future__ import annotations

import asyncio
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
AI_CONCURRENCY = 3
MAX_TITLE = 120

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


def build_plan(
    root: Path,
    videos: list[Path],
    extra_paths: set[str],
    titles: dict[str, str] | None = None,
) -> ExplainedPlan:
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

    cleaned = titles or {}
    # 模型偶尔把多个文件清洗成同一个名字：这类退化结果不如规则名，退回规则
    counts: dict[str, int] = {}
    for path in extras:
        value = cleaned.get(path.as_posix())
        if value:
            counts[value] = counts.get(value, 0) + 1
    for path in sorted(extras, key=lambda item: item.name.lower()):
        value = cleaned.get(path.as_posix())
        if not value or counts.get(value, 0) > 1:
            value = _extra_title(path)
        items.append(PlannedItem(path, "extra", 0, None, f"extras/{path.name}", value))
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

    chunks = [ordered[start : start + CHUNK_SIZE] for start in range(0, len(ordered), CHUNK_SIZE)]
    results = await _gather_chunks(client, chunks, build_prompt, parse_indices, "结构识别")
    for chunk, indices in zip(chunks, results, strict=True):
        if indices is None:
            logger.info("AI 结构未通过校验，退回规则")
            return None
        for index in indices:
            extra_paths.add(chunk[index - 1].as_posix())

    if not extra_paths:
        logger.info("AI 结构：模型判定这批全部是正片")
        return build_plan(root, videos, extra_paths)
    extras = [path for path in ordered if path.as_posix() in extra_paths]
    titles = await clean_titles(client, extras)
    return build_plan(root, videos, extra_paths, titles)

_TITLE_PROMPT = """下面是番剧特典文件的原始名字（编号: 名字）：

{files}

请为每一个把名字清洗成可读的中文名：去掉发布组 [VCB-Studio] 这类方括号、
分辨率、编码（Ma10p/1080p/x265/flac）、集号方括号等冗余信息，保留作品名和特典本身的名称。

只输出下面这种行，一行一个，不要解释：
编号|清洗后的名字
"""


def build_title_prompt(videos: list[Path]) -> str:
    lines = "\n".join(f"{index + 1}: {video.stem}" for index, video in enumerate(videos))
    return _TITLE_PROMPT.format(files=lines)


def parse_titles(reply: str, expected: int) -> dict[int, str] | None:
    """解析 `编号|名字`；必须完整覆盖，否则视为失败。"""
    found: dict[int, str] = {}
    for raw in (reply or "").splitlines():
        line = raw.strip().strip("`")
        if "|" not in line and "｜" not in line:
            continue
        head, _, tail = line.replace("｜", "|").partition("|")
        try:
            index = int(head.strip().split()[-1])
        except (ValueError, IndexError):
            continue
        if not (1 <= index <= expected):
            continue
        title = tail.strip()[:MAX_TITLE]
        if title:
            found[index] = title
    if len(found) != expected:
        return None
    return found


async def _gather_chunks(client, chunks: list[list[Path]], prompt, parse, label: str):
    """并发跑批次，结果按原顺序返回；任一批失败返回 None。"""
    gate = asyncio.Semaphore(AI_CONCURRENCY)

    async def one(chunk: list[Path]):
        async with gate:
            try:
                reply = await client(prompt(chunk))
            except Exception as exc:  # noqa: BLE001
                logger.info("AI %s失败: %s", label, type(exc).__name__)
                return None
            return parse(reply or "", len(chunk))

    return await asyncio.gather(*(one(chunk) for chunk in chunks))


async def clean_titles(
    client,
    paths: list[Path],
    *,
    chunk_size: int = 10,
) -> dict[str, str]:
    """让模型清洗特典名；任何一批失败就整体放弃（调用方用规则名兜底）。"""
    chunks = [paths[start : start + chunk_size] for start in range(0, len(paths), chunk_size)]
    if not chunks:
        return {}
    results = await _gather_chunks(client, chunks, build_title_prompt, parse_titles, "标题清洗")
    result: dict[str, str] = {}
    for chunk, titles in zip(chunks, results, strict=True):
        if titles is None:
            logger.info("AI 标题清洗未通过校验，改用规则名")
            return {}
        for position, path in enumerate(chunk, start=1):
            result[path.as_posix()] = titles[position]
    return result