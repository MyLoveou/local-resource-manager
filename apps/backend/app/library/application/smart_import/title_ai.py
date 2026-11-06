"""AI 兜底：让文本模型从候选片段里**挑选**，不允许自由生成标题。

设计约束（对应 L1 §7 的"建议要可解释、可回退"）：

1. 模型只能回答"保留第几段"，返回下标；
2. 下标越界或 JSON 不合法 → 直接丢弃，退回规则结果；
3. 结果由原始片段拼接而成，**不可能出现输入里没有的字**；
4. 模型不可用 / 超时 / 空回复 → 静默降级，规则结果照常使用。
"""

from __future__ import annotations

import json
import re
from dataclasses import replace

from app.library.application.smart_import.base import ActionContext, Suggestion
from app.library.application.smart_import.suspect import needs_review
from app.library.application.smart_import.title_clean import split_segments
from app.shared.log import logger

PROMPT_VERSION = "title-ai-v1"

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

# 进程内缓存：同一串片段只问一次模型
_CACHE: dict[tuple[str, ...], str | None] = {}

_PROMPT = """你在帮一个本地媒体库整理番剧标题。
下面是从一个发布名里拆出的片段，编号从 0 开始：
{segments}

用户的期望是：只保留**作品名**，去掉发布组、集数范围、全集/特典说明、分辨率、编码、音轨、语言与容器。
可能的作品名参考（来自这个库，仅为提示，可能为空）：{known}

只输出 JSON，格式：{{"keep": [作品名所在的片段编号]}}
不要输出任何解释、不要改写文字、不要翻译。
"""


def reset_cache() -> None:
    """清空进程内缓存（测试与设置变更后使用）。"""
    _CACHE.clear()


def build_prompt(segments: list[str], known_titles: tuple[str, ...] = ()) -> str:
    numbered = "\n".join(f"{index}: {segment}" for index, segment in enumerate(segments))
    known = "、".join(known_titles[:5]) if known_titles else "（无）"
    return _PROMPT.format(segments=numbered, known=known)


def parse_selection(reply: str, segments: list[str]) -> list[int] | None:
    """从模型回复里取出保留下标；不合法返回 None。"""
    if not reply:
        return None
    block = _JSON_BLOCK.search(reply)
    if block is None:
        return None
    try:
        data = json.loads(block.group(0))
    except json.JSONDecodeError:
        return None
    raw = data.get("keep") if isinstance(data, dict) else None
    if not isinstance(raw, list) or not raw:
        return None
    picked: list[int] = []
    for item in raw:
        if not isinstance(item, int) or isinstance(item, bool):
            return None
        if item < 0 or item >= len(segments):
            return None
        if item not in picked:
            picked.append(item)
    return sorted(picked)


def compose_title(segments: list[str], picked: list[int]) -> str:
    """按下标拼回标题；相邻中文片段不加空格。"""
    chosen = [segments[index].strip() for index in picked if segments[index].strip()]
    if not chosen:
        return ""
    out = chosen[0]
    for piece in chosen[1:]:
        separator = "" if _ends_cjk(out) and _starts_cjk(piece) else " "
        out = f"{out}{separator}{piece}"
    return re.sub(r"\s+", " ", out).strip(" -–—_·.")


def _ends_cjk(text: str) -> bool:
    return bool(text) and "\u4e00" <= text[-1] <= "\u9fff"


def _starts_cjk(text: str) -> bool:
    return bool(text) and "\u4e00" <= text[0] <= "\u9fff"


async def suggest_title(
    raw_name: str,
    *,
    complete,
    known_titles: tuple[str, ...] = (),
) -> tuple[str, list[str]] | None:
    """返回 (标题, 片段列表)；模型不可用或结果不合法返回 None。"""
    segments = split_segments(raw_name)
    if len(segments) < 2:
        return None
    key = tuple(segments)
    if key in _CACHE:
        return _CACHE[key], list(segments)
    try:
        reply = await complete(build_prompt(list(segments), known_titles))
    except Exception as exc:  # noqa: BLE001 - 兜底失败不影响导入
        logger.info("AI 标题建议失败: %s", type(exc).__name__)
        return None
    picked = parse_selection(reply or "", list(segments))
    if not picked:
        return None
    title = compose_title(list(segments), picked)
    if not title or needs_review(raw_name, title):
        return None
    # 只缓存成功：一次超时不该让这个名字永久失去兜底机会
    _CACHE[key] = title
    return title, list(segments)


async def refine_suggestions(
    ctx: ActionContext,
    suggestions: list[Suggestion],
    *,
    complete=None,
    known_titles: tuple[str, ...] = (),
    enabled: bool = False,
) -> list[Suggestion]:
    """只对"规则拿不准"的标题建议做 AI 兜底；未开启 AI 时原样返回。"""
    if not suggestions or not enabled:
        return suggestions
    from app.ai.infrastructure.text_completion import complete as default_complete

    client = complete or default_complete
    out: list[Suggestion] = []
    for suggestion in suggestions:
        if suggestion.field != "title":
            out.append(suggestion)
            continue
        raw = ctx.dir_name or ctx.file_stem
        if not raw:
            out.append(suggestion)
            continue
        result = await suggest_title(raw, complete=client, known_titles=known_titles)
        if result is None:
            out.append(suggestion)
            continue
        title, _ = result
        out.append(
            replace(
                suggestion,
                value={"text": title},
                confidence=0.9,
                reason="AI 从发布名片段中选出作品名",
                source="ai",
            )
        )
    return out


async def ai_only_suggestion(
    ctx: ActionContext,
    *,
    complete=None,
    known_titles: tuple[str, ...] = (),
) -> Suggestion | None:
    """规则没产出标题建议时，直接让模型选出作品名。"""
    from app.ai.infrastructure.text_completion import complete as default_complete

    raw = ctx.dir_name or ctx.file_stem
    if not raw:
        return None
    result = await suggest_title(
        raw, complete=complete or default_complete, known_titles=known_titles
    )
    if result is None:
        return None
    title, _ = result
    return Suggestion(
        field="title",
        value={"text": title},
        confidence=0.9,
        reason="AI 从发布名片段中选出作品名",
        source="ai",
    )
