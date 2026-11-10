"""Small query planner for AI image search.

The first version only derives hard attributes that can be checked without a
language model: visible person count and image orientation. Everything else
stays as CLIP semantic text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ai.application.labels import labels_in_query


@dataclass(frozen=True)
class AttributeFilter:
    feature: str
    op: str
    value: int | str
    label: str


@dataclass
class ParsedQuery:
    text: str
    filters: list[AttributeFilter] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


# Keep the more specific phrases first. Count parsing intentionally stops after
# one count phrase so "两个人合影" does not create a redundant >=2 filter.
_COUNT_RULES: tuple[tuple[str, str, int, str], ...] = (
    (r"(没有人|无人|空镜)", "eq", 0, "人数=0"),
    (r"(一个人|单人|独自|一位|1个人|1人|1位)", "eq", 1, "人数=1"),
    (r"(两个人|双人|二人|两位|情侣|两个女生|两个男生|两个女孩|两个男孩|2个人|2人|2位)", "eq", 2, "人数=2"),
    (r"(三个人|三人|三个女生|三个男生|3个人|3人|3位)", "eq", 3, "人数=3"),
    (r"(四个人|四人|4个人|4人|4位)", "eq", 4, "人数=4"),
    (r"(五个人|五人|5个人|5人|5位)", "eq", 5, "人数=5"),
    (r"(多人|一群人|好几个人|很多人)", "gte", 3, "人数≥3"),
    (r"(合影|合照)", "gte", 2, "人数≥2"),
    (r"(有人)", "gte", 1, "人数≥1"),
)

_ORIENTATION_RULES: tuple[tuple[str, str, str], ...] = (
    (r"(横图|横屏|横向|横版)", "landscape", "横图"),
    (r"(竖图|竖屏|竖向|竖版)", "portrait", "竖图"),
    (r"(方图|正方形)", "square", "方图"),
)


def _remove(pattern: str, text: str) -> tuple[str, str | None]:
    match = re.search(pattern, text)
    if match is None:
        return text, None
    return f"{text[:match.start()]} {text[match.end():]}", match.group(1)


def parse_query(raw: str) -> ParsedQuery:
    text = raw.strip()
    filters: list[AttributeFilter] = []
    labels = labels_in_query(raw)

    for pattern, op, value, label in _COUNT_RULES:
        text, phrase = _remove(pattern, text)
        if phrase is None:
            continue
        filters.append(AttributeFilter("person_count", op, value, label))
        break

    # Arabic numerals are handled after the Chinese phrases.
    if not any(item.feature == "person_count" for item in filters):
        match = re.search(r"(\d+)\s*个?人", text)
        if match is not None:
            count = max(0, min(20, int(match.group(1))))
            filters.append(AttributeFilter("person_count", "eq", count, f"人数={count}"))
            text = f"{text[:match.start()]} {text[match.end():]}"

    for pattern, value, label in _ORIENTATION_RULES:
        text, phrase = _remove(pattern, text)
        if phrase is None:
            continue
        filters.append(AttributeFilter("orientation", "eq", value, label))
        break

    text = re.sub(r"\s+", " ", text).strip(" ，,。；;")
    if not text:
        if any(item.feature == "person_count" for item in filters):
            if any(item.value == 0 for item in filters):
                text = "空镜"
            elif any(
                isinstance(item.value, int) and item.value >= 2 for item in filters
            ):
                text = "人物合影"
            else:
                text = "人物"
        elif any(item.feature == "orientation" for item in filters):
            text = "照片"
    return ParsedQuery(text=text or raw.strip(), filters=filters, labels=labels)
