"""发布组命名清洗（纯函数，不碰 DB 与网络）。

只处理「文件名 / 目录名 → 更像标题的字符串」，不改磁盘文件名。
置信度用于前端分档：>=0.85 默认勾选，0.5–0.85 展示不勾，<0.5 折叠。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 方括号 / 圆括号 / 全角括号
_BRACKET = re.compile(r"[\[\(（【]([^\[\]\(\)（）【】]*)[\]\)）】]")

_TOKEN_SPLIT = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")
_HAS_CJK = re.compile(r"[\u4e00-\u9fff]")
_DIGITS_ONLY = re.compile(r"^\d{1,4}$")

# 特典类标记的中文写法：单文件视频里 `Tokuten` 直接显示成「特典」
_EXTRA_WORD_MAP = {"tokuten": "特典", "extra": "特典", "extras": "特典"}

_NOISE_TOKENS = frozenset(
    {
        # 分辨率
        "480p", "720p", "1080p", "1080i", "2160p", "1440p",
        "4k", "8k", "uhd", "hd", "fhd", "qhd",
        # 编码 / 位深
        "x264", "x265", "h264", "h265", "hevc", "avc", "av1", "vp9",
        "ma10p", "hi10p", "10bit", "8bit", "10bits",
        # 音轨
        "aac", "ac3", "eac3", "dts", "dtshd", "flac", "opus", "mp3",
        "mp4a", "truehd", "lpcm", "atmos",
        # 来源
        "webdl", "webrip", "web", "dl", "rip", "bd", "bdrip", "bdremux",
        "bluray", "blu", "hdtv", "dvdrip", "remux", "dvd",
        # 语言 / 字幕
        "chs", "cht", "gb", "big5", "jpn", "eng", "sc", "tc", "jpsc", "jptc",
        # 容器
        "mp4", "mkv", "avi", "flv", "ts", "m4v", "mov", "wmv",
        # 站点
        "baha", "bilibili", "cr", "adn", "nf", "amzn", "dsnp", "abema",
    }
)

# 中文噪音：字幕组 / 压制 / 搬运等（任何场景都剥）
_NOISE_CJK = ("字幕组", "字幕", "压制", "搬运", "生肉", "熟肉", "汉化", "翻译")

# 打包/特典/语言包装：只在**作品标题**里剥。
# 单文件视频靠这些词区分集与特典，剥掉会撞名（`异世界舅舅 01` vs 特典第 01 集）。
_PACK_CJK = (
    "全集", "合集", "完结合集", "全话", "本篇",
    "特典", "映像特典", "特典映像", "预告", "花絮", "菜单",
    "双语", "外挂", "内封", "内嵌", "简繁", "简体", "繁体", "中日",
)

# 集数范围：`01-13`、`1~12`、`01-13TV`。整段视为打包说明，不是标题
_EPISODE_RANGE = re.compile(r"\d{1,3}\s*[-~～–—]\s*\d{1,3}")

# 英文特典标记：只在作品标题里剥。单文件视频靠它们区分正片与特典
_PACK_WORDS = frozenset(
    {"pv", "tokuten", "extra", "extras", "special", "specials", "ncop", "nced", "ova", "oad", "menu", "cm"}
)

# 话数说明：`全12话`、`12集`（中间夹数字，字符串匹配覆盖不到）
_FULL_COUNT = re.compile(r"全\s*\d{1,4}\s*[话集部]|\d{1,4}\s*[话集]")

# 尾部署编号：` - 01`、` 01`、`_01`、` 第01话`、` 第3集`
_TRAILING_EP = re.compile(r"(?:[\s_\-–—]+|^)(?:第\s*)?(\d{1,4})(?:\s*[话集期])?\s*$")

# 季/集标记：属于系列结构，不进作品标题
_SERIES_MARKERS = (
    re.compile(r"第\s*\d{1,2}\s*[季部章]"),
    re.compile(r"\bseason\s*\d{1,2}\b", re.IGNORECASE),
    re.compile(r"\bs\d{1,2}e\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\bs\d{1,2}\b", re.IGNORECASE),
    re.compile(r"\be(?:p)?\d{1,3}\b", re.IGNORECASE),
    re.compile(r"\bepisode\s*\d{1,3}\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class CleanResult:
    """清洗结果。`removed` 是被人话解释用的原始片段。"""

    title: str
    removed: tuple[str, ...]
    confidence: float


def split_segments(raw: str) -> list[str]:
    """把发布名按括号拆成片段，供 AI 兜底挑选（不含括号本身）。"""
    return [m.group(1).strip() for m in _BRACKET.finditer(raw or "") if m.group(1).strip()]


def _tokens(segment: str) -> list[str]:
    return [t.lower() for t in _TOKEN_SPLIT.split(segment) if t]


def _is_noise_tokens(segment: str, *, work_title: bool = False) -> bool:
    if any(marker in segment for marker in _NOISE_CJK):
        return True
    if work_title and any(marker in segment for marker in _PACK_CJK):
        return True
    if work_title and _FULL_COUNT.search(segment):
        return True
    if work_title and any(token in _PACK_WORDS for token in _tokens(segment)):
        return True
    # `01-13TV全集` 这类打包段：集数范围本身就是噪音
    if _EPISODE_RANGE.search(segment):
        return True
    tokens = _tokens(segment)
    if not tokens:
        return True
    return all(token in _NOISE_TOKENS or token.isdigit() for token in tokens)


def _looks_like_group(segment: str) -> bool:
    """首个方括号段、无中文、短、像发布组。"""
    text = segment.strip()
    if not text or _HAS_CJK.search(text):
        return False
    if len(text) > 24:
        return False
    if any(token in _NOISE_TOKENS for token in _tokens(text)):
        return False
    return True


def _join_pieces(pieces: list[str]) -> str:
    """拼接片段：中文相邻不加空格，其余加空格。

    `[Isekai Ojisan][PV][08]` 以前拼成 `Isekai OjisanPV 08`，读不成词组。
    """
    out = ""
    for piece in pieces:
        text = piece.strip()
        if not text:
            continue
        if not out:
            out = text
            continue
        separator = "" if (_ends_cjk(out) and _starts_cjk(text)) else " "
        out = f"{out}{separator}{text}"
    return out


def _ends_cjk(text: str) -> bool:
    return bool(text) and "\u4e00" <= text[-1] <= "\u9fff"


def _starts_cjk(text: str) -> bool:
    return bool(text) and "\u4e00" <= text[0] <= "\u9fff"


def clean_release_name(raw: str, *, keep_episode: bool = True) -> CleanResult:
    """去掉发布组、参数、语言、容器等噪音，保留标题。

    `keep_episode=True`（默认）保留季/集标记与尾部编号：单文件视频每个文件
    就是一个独立资源，编号是它唯一的区分依据，剥掉会让多集同名。
    `keep_episode=False` 用于系列作品标题：集号属于季/集树，不进作品名。
    """
    source = (raw or "").strip()
    if not source:
        return CleanResult(title="", removed=(), confidence=0.0)

    removed: list[str] = []
    pieces: list[str] = []
    cursor = 0
    first_bracket = True

    for match in _BRACKET.finditer(source):
        pieces.append(source[cursor:match.start()])
        cursor = match.end()
        inner = match.group(1).strip()

        if _DIGITS_ONLY.match(inner):
            if keep_episode:
                pieces.append(inner)
            else:
                removed.append(match.group(0))
            first_bracket = False
            continue

        if _is_noise_tokens(inner, work_title=not keep_episode) or (
            first_bracket and _looks_like_group(inner)
        ):
            removed.append(match.group(0))
        else:
            pieces.append(_EXTRA_WORD_MAP.get(inner.lower(), inner))
        first_bracket = False

    pieces.append(source[cursor:])
    title = _join_pieces(pieces)

    # 季/集标记属于系列结构；单文件视频靠它区分集，必须保留
    if not keep_episode:
        for pattern in _SERIES_MARKERS:
            found = [match.group(0).strip() for match in pattern.finditer(title)]
            if found:
                removed.extend(found)
                title = pattern.sub(" ", title)

    match = _TRAILING_EP.search(title)
    if match is not None:
        if keep_episode:
            # 归一成两位编号，但保留集号本身
            number = int(match.group(1))
            title = f"{title[: match.start()].rstrip()} {number:02d}"
        else:
            removed.append(match.group(0).strip())
            title = title[: match.start()]

    title = re.sub(r"\s+", " ", title).strip(" -–—_·.")
    if not title:
        return CleanResult(title=source, removed=tuple(removed), confidence=0.1)

    if not removed:
        return CleanResult(title=title, removed=(), confidence=0.0)

    confidence = min(0.95, 0.55 + 0.1 * len(removed))
    return CleanResult(title=title, removed=tuple(removed), confidence=confidence)


def describe_removed(removed: tuple[str, ...]) -> str:
    """把被去掉的片段写成一句人话，供建议的 reason 使用。"""
    if not removed:
        return ""
    parts = "、".join(f"`{item}`" for item in removed)
    return f"去掉了 {parts}"
