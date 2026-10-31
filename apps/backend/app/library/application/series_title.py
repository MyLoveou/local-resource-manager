"""作品标题：目录名/文件名 → 干净的作品名。

导入时资源标题直接取 `root.name`，于是库里会出现
`[VCB-Studio] Kami nomi zo Shiru Sekai [Ma10p_1080p]` 这种带发布组和编码的名字。

规则清洗覆盖大部分方括号噪声；点分命名（`Show.S01.1080p.BluRay`）和中日文后缀
交给模型，模型不可用时退回规则结果。
"""

from __future__ import annotations

import re
from pathlib import Path

from app.library.application.smart_import.title_clean import clean_release_name
from app.shared.log import logger

MAX_TITLE = 120

_DOTTED = re.compile(r"[._]")
_NOISE = re.compile(
    r"\b(?:1080p|720p|2160p|4k|bluray|bdrip|webrip|web-dl|hdtv|hevc|x264|x265|"
    r"aac|flac|ma10p|10bit|8bit|uncensored)\b",
    re.IGNORECASE,
)
_SEASON_TAIL = re.compile(r"\s*(?:s\d{1,2}|season\s*\d{1,2}|第\s*\d{1,2}\s*季)$", re.IGNORECASE)

_PROMPT = """把下面这个番剧目录名清洗成作品名。

目录名：{name}

要求：
- 去掉发布组（如 [VCB-Studio]）、分辨率、编码、字幕语言、季数等附加信息
- 保留作品本身的名称，原文是哪种语言就保持哪种语言
- 只输出作品名一行，不要解释、不要引号
"""


def rule_title(name: str) -> str:
    """先用规则清洗；清不动时把点分命名还原成空格再试。"""
    cleaned = clean_release_name(name).title.strip()
    if cleaned and cleaned != name:
        return cleaned[:MAX_TITLE]
    spaced = _DOTTED.sub(" ", name).strip()
    if spaced != name:
        without_noise = re.sub(r"\s{2,}", " ", _NOISE.sub(" ", spaced)).strip()
        without_noise = _SEASON_TAIL.sub("", without_noise).strip()
        candidate = without_noise.strip(" -_.")
        if candidate:
            return candidate[:MAX_TITLE]
    return (cleaned or name)[:MAX_TITLE]


def parse_title_reply(reply: str) -> str | None:
    """模型只该回一行标题；多行取第一行，去掉引号和代码块。"""
    for raw in (reply or "").splitlines():
        line = raw.strip().strip("`").lstrip("#").lstrip("-*").strip().strip('"').strip("'").strip()
        if not line:
            continue
        if len(line) > MAX_TITLE:
            line = line[:MAX_TITLE]
        return line or None
    return None


async def series_title(name: str, *, complete=None) -> str:
    """目录名 → 作品名；模型失败时退回规则结果，不会返回空。"""
    fallback = rule_title(name)
    if complete is None:
        return fallback
    try:
        reply = await complete(_PROMPT.format(name=name))
    except Exception as exc:  # noqa: BLE001 - 标题清洗失败不该中断导入
        logger.info("AI 标题清洗失败: %s", type(exc).__name__)
        return fallback
    candidate = parse_title_reply(reply or "")
    if not candidate:
        return fallback
    # 模型把整段原名原样还回来（含方括号）时，规则结果更可信
    if candidate == name and fallback != name:
        return fallback
    return candidate


def title_from_path(path: Path) -> str:
    """同步入口：只要规则清洗（用于不需要模型的路径）。"""
    return rule_title(path.stem if path.suffix else path.name)


async def ai_title_for(root: Path, resources) -> str:
    """导入入口用：AI 开关开启时走模型，否则只用规则。

    仓储从调用方传入——导入有不止一条路径，`self._resources` 不一定有值。
    """
    from app.library.application.smart_import.preferences import is_ai_enabled

    fallback = rule_title(root.name)
    try:
        if not await is_ai_enabled(resources._session):
            return fallback
        from app.ai.infrastructure.text_completion import complete

        return await series_title(root.name, complete=complete)
    except Exception as exc:  # noqa: BLE001 - 标题失败不该中断导入
        logger.info("标题清洗退回规则: %s", type(exc).__name__)
        return fallback