"""AI 主导的系列结构拆分。

开启「智能导入使用 AI」时，由模型决定**每个文件是第几季第几集还是特典**，
规则层只做校验与落盘。校验不通过就整体丢弃、退回规则——宁可退回，也不接受
半对的结构（错挂的集比不挂更难发现）。

安全边界：模型只能给**已存在的文件**打标签，不能改名、增删文件、改集号顺序。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

from app.library.application.series_plan import (
    ExplainedPlan,
    PlannedItem,
    _extra_title,
    _ok,
)
from app.shared.log import logger

PROMPT_VERSION = "series-plan-v1"

MAX_SEASON = 99
MAX_EPISODE = 999
MAX_TITLE = 120

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

_PROMPT = """你在为一个本地媒体库整理一个番剧目录。

下面是这个目录里的视频文件（不含扩展名的相对名）：
{files}

请判断每个文件属于哪一季的哪一集，或者它其实是特典（OVA、角色歌、映像、CD 等）。

只输出 JSON，格式：
{{"files": [{{"name": "文件名（必须与上面完全一致）", "kind": "episode", "season": 1, "episode": 3}}, {{"name": "...", "kind": "extra", "title": "特典名"}}]}}

规则：
- 每个文件必须出现且只出现一次
- season 从 1 开始；episode 从 1 开始；同一季内集号不能重复
- 特典用 kind=extra，可给 title；正片不要给 title
- 不要输出解释，不要改文件名
"""


@dataclass(frozen=True)
class AISeriesItem:
    name: str
    kind: str
    season: int = 1
    episode: int | None = None
    title: str | None = None


def _norm(text: str) -> str:
    """归一化文件名：去扩展名、去空白与符号、小写。"""
    stem = Path(text).stem or text
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", stem.lower())


def build_prompt(videos: list[Path]) -> str:
    names = "\n".join(f"{index + 1}. {video.stem}" for index, video in enumerate(videos))
    return _PROMPT.format(files=names)


def parse_reply(reply: str, videos: list[Path]) -> list[AISeriesItem] | None:
    """解析并校验模型输出；任何一条不合法都整份丢弃。"""
    if not reply:
        return None
    block = _JSON_BLOCK.search(reply)
    if block is None:
        return None
    try:
        data = json.loads(block.group(0))
    except json.JSONDecodeError:
        return None
    rows = data.get("files") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None

    by_stem = {video.stem: video for video in videos}
    # 宽松匹配：模型偶尔会带上扩展名或改动空格/大小写，按归一化名兜一层
    by_norm = {_norm(video.stem): video.stem for video in videos}
    seen: dict[str, AISeriesItem] = {}
    used: set[tuple[int, int]] = set()
    for row in rows:
        if not isinstance(row, dict):
            return None
        name = str(row.get("name") or "").strip()
        stem = Path(name).stem or name
        if stem not in by_stem:
            stem = by_norm.get(_norm(stem), stem)
        if stem not in by_stem or stem in seen:
            return None
        kind = str(row.get("kind") or "").strip().lower()
        if kind == "extra":
            title = str(row.get("title") or "").strip()[:MAX_TITLE] or None
            seen[stem] = AISeriesItem(name=stem, kind="extra", title=title)
            continue
        if kind != "episode":
            return None
        season = row.get("season")
        episode = row.get("episode")
        if not isinstance(season, int) or isinstance(season, bool):
            return None
        if not isinstance(episode, int) or isinstance(episode, bool):
            return None
        if not (1 <= season <= MAX_SEASON) or not (1 <= episode <= MAX_EPISODE):
            return None
        if (season, episode) in used:
            return None
        used.add((season, episode))
        seen[stem] = AISeriesItem(
            name=stem, kind="episode", season=season, episode=episode
        )
    if set(seen) != set(by_stem):
        return None
    return [seen[stem] for stem in by_stem]


def validate_reply(
    reply: str, videos: list[Path]
) -> tuple[list[AISeriesItem] | None, str]:
    """解析并给出失败原因，便于在日志里定位"模型到底错在哪"。"""
    items = parse_reply(reply, videos)
    if items is not None:
        return items, ""
    block = _JSON_BLOCK.search(reply or "")
    if block is None:
        return None, "回复里没有 JSON"
    try:
        data = json.loads(block.group(0))
    except json.JSONDecodeError:
        return None, "JSON 解析失败"
    rows = data.get("files") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None, "缺少 files 数组"
    names = {
        str(row.get("name") or "").strip() for row in rows if isinstance(row, dict)
    }
    return None, f"返回 {len(names)} 个不同文件，输入 {len(videos)} 个（可能被截断或改名）"


def to_plan(root: Path, videos: list[Path], items: list[AISeriesItem]) -> ExplainedPlan:
    by_stem = {video.stem: video for video in videos}
    planned: list[PlannedItem] = []
    for item in items:
        path = by_stem[item.name]
        if item.kind == "episode" and item.episode is not None:
            dest = (
                f"seasons/{item.season:02d}/S{item.season:02d}E{item.episode:02d}"
                f"{path.suffix.lower()}"
            )
            planned.append(PlannedItem(path, "episode", item.season, item.episode, dest, None))
        else:
            planned.append(
                PlannedItem(
                    path, "extra", 0, None, f"extras/{path.name}", item.title or _extra_title(path)
                )
            )
    plan = _ok(planned, 0)
    return replace(plan, message=f"AI 识别：{plan.message}")


async def plan_with_ai(
    root: Path,
    videos: list[Path],
    *,
    complete=None,
) -> ExplainedPlan | None:
    """模型主导的结构；不可用或结果不合法返回 None（由调用方退回规则）。"""
    if len(videos) < 2:
        return None
    from app.ai.infrastructure.text_completion import complete as default_complete

    client = complete or default_complete
    try:
        reply = await client(build_prompt(videos))
    except Exception as exc:  # noqa: BLE001 - 模型失败不该中断导入
        logger.info("AI 结构识别失败: %s", type(exc).__name__)
        return None
    items, reason = validate_reply(reply or "", videos)
    if items is None:
        logger.info("AI 结构未通过校验：%s", reason)
        return None
    return to_plan(root, videos, items)
