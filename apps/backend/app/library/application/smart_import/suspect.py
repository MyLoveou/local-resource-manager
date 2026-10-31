"""可疑残留检测：规则剥完之后，还剩"像参数、像打包"的东西就标记出来。

目的不是自动再剥一次，而是**在建议里说清楚"我不确定"**——让审阅面板提示人工确认，
或交给后续的 AI 兜底处理。
"""

from __future__ import annotations

import re

# 残留的参数词：正常标题不会出现
_PARAM_TOKENS = (
    "h264", "h265", "x264", "x265", "hevc", "avc", "av1",
    "480p", "720p", "1080p", "1080i", "1440p", "2160p", "4k", "8k", "uhd",
    "10bit", "8bit", "ma10p", "hi10p",
    "aac", "flac", "dts", "truehd", "atmos",
    "webrip", "webdl", "bdrip", "bluray", "remux", "hdtv",
)

# 数字与字母粘连：`13tv`、`01bd`
_MIXED = re.compile(r"\d{1,4}[A-Za-z]{2,}")

# 集数范围残留：`01-13`
_RANGE = re.compile(r"\d{1,3}\s*[-~～–—]\s*\d{1,3}")

# 连接符：打包段常见
_CONNECT = re.compile(r"[+&]")

_BRACKETS = (("（", "）"), ("【", "】"), ("(", ")"), ("[", "]"))

# 超过这个长度基本不可能是作品名
_TOO_LONG = 24


def suspicion_reasons(raw: str, title: str) -> tuple[str, ...]:
    """返回可疑原因（人话）；空元组表示规则清洗结果看起来干净。"""
    reasons: list[str] = []
    if not title:
        return ("标题为空",)

    if _RANGE.search(title):
        reasons.append("仍含集数范围")
    if _CONNECT.search(title):
        reasons.append("仍含 + / & 连接符")
    if _MIXED.search(title):
        reasons.append("数字与字母粘连")
    lowered = title.lower()
    leftover = [token for token in _PARAM_TOKENS if token in lowered]
    if leftover:
        reasons.append("仍含参数词 " + "、".join(leftover[:3]))
    if len(title) > _TOO_LONG:
        reasons.append(f"长度 {len(title)} 偏长")
    for left, right in _BRACKETS:
        if raw.count(left) != raw.count(right):
            reasons.append("原始名称括号不配对")
            break
    return tuple(reasons)


def describe_suspicion(reasons: tuple[str, ...]) -> str:
    if not reasons:
        return ""
    return "可疑残留：" + "、".join(reasons)


def needs_review(raw: str, title: str) -> bool:
    return bool(suspicion_reasons(raw, title))
