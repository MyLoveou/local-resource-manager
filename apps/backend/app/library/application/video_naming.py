"""视频文件名元数据解析：内置 bilidown 规则 + 用户自定义规则，兜底返回 None（标题用 stem）。

用户规则存 settings KV（KEY_PARSE），命名组约定：title / author / bv / ep / date。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.settings.domain.constants import KEY_PARSE
from app.settings.infrastructure.settings_repo import SettingsRepository

# 内置：bilidown 合集命名
# 43-UP 浪浪山小蛋仔-BV1FWHk6VEVA-2026-10-7-不烧心的瓜不卖【AI全民制作人】-132K  mp4a-1080P+ 高码率  avc1
_BILIDOWN = re.compile(
    r"^(?P<ep>\d+)-UP\s+(?P<author>.+?)-(?P<bv>BV1[0-9A-Za-z]{9})-(?P<date>\d{4}-\d{1,2}-\d{1,2})-(?P<rest>.+)$",
    re.IGNORECASE,
)

# 尾部质量噪音起点：-数字K/M 后跟音频/分辨率噪音（132K mp4a-1080P+…）
_QUALITY_TAIL = re.compile(r"-(\d+(?:\.\d+)?[KM])\s", re.IGNORECASE)

_user_rules_cache: list[re.Pattern] | None = None
_options_cache: dict | None = None


@dataclass(frozen=True)
class ParsedVideoName:
    """文件名解析结果；字段为空表示未提取。"""

    title: str | None = None
    author: str | None = None
    bv: str | None = None
    ep: int | None = None
    date: str | None = None


@dataclass(frozen=True)
class ParseSettings:
    """解析设置：用户规则 + 两个开关。"""

    rules: tuple[re.Pattern, ...] = ()
    title_with_ep: bool = False
    auto_collection: bool = False


def _strip_quality_tail(text: str) -> str:
    match = _QUALITY_TAIL.search(text)
    return text[: match.start()].strip() if match else text.strip()


def _from_groups(groups: dict) -> ParsedVideoName:
    title = groups.get("title")
    author = groups.get("author")
    bv = groups.get("bv")
    ep = groups.get("ep")
    date = groups.get("date")
    return ParsedVideoName(
        title=_strip_quality_tail(str(title).strip()) if title else None,
        author=str(author).strip() if author else None,
        bv=str(bv).strip().upper() if bv else None,
        ep=int(ep) if ep is not None and str(ep).isdigit() else None,
        date=str(date).strip() if date else None,
    )


def compile_user_rules(raw_rules: list[str]) -> list[re.Pattern]:
    """把设置里的正则文本编译为 Pattern；无效项跳过（保存时已校验）。"""
    compiled: list[re.Pattern] = []
    for text in raw_rules or []:
        if not text.strip():
            continue
        try:
            compiled.append(re.compile(text.strip()))
        except re.error:
            continue
    return compiled


async def load_user_rules(session) -> list[re.Pattern]:
    """用户自定义解析规则（进程级缓存，设置保存后失效）。"""
    settings = await load_parse_settings(session)
    return list(settings.rules)


async def load_parse_settings(session) -> ParseSettings:
    """解析设置：用户规则 + titleWithEp + autoCollection（进程级缓存）。"""
    global _user_rules_cache, _options_cache
    if _user_rules_cache is None or _options_cache is None:
        raw = await SettingsRepository(session).get_json(KEY_PARSE)
        rules = raw.get("rules")
        _user_rules_cache = compile_user_rules(rules if isinstance(rules, list) else [])
        _options_cache = {
            "titleWithEp": bool(raw.get("titleWithEp")),
            "autoCollection": bool(raw.get("autoCollection")),
        }
    return ParseSettings(
        rules=tuple(_user_rules_cache),
        title_with_ep=bool(_options_cache.get("titleWithEp")),
        auto_collection=bool(_options_cache.get("autoCollection")),
    )


def invalidate_user_rules() -> None:
    global _user_rules_cache, _options_cache
    _user_rules_cache = None
    _options_cache = None


def parse_video_name(stem: str, user_rules: list[re.Pattern] | None = None) -> ParsedVideoName | None:
    """按 用户规则 → 内置 bilidown 顺序解析；都不匹配返回 None。"""
    for pattern in user_rules or []:
        match = pattern.search(stem)
        if match is None:
            continue
        return _from_groups(match.groupdict())
    match = _BILIDOWN.search(stem)
    if match is None:
        return None
    groups = match.groupdict()
    rest = groups.get("rest")
    groups["title"] = rest
    return _from_groups(groups)
