"""清晰度 / 画质展示档（不落库）。阈值与映射集中定义，调用处只查表。"""

from __future__ import annotations

CLARITY_STANDARD: dict[tuple[int, int], str] = {
    (7680, 4320): "8K",
    (4320, 7680): "8K",
    (3840, 2160): "4K",
    (2160, 3840): "4K",
    (2560, 1440): "1440p",
    (1440, 2560): "1440p",
    (1920, 1080): "1080p",
    (1080, 1920): "1080p",
    (1280, 720): "720p",
    (720, 1280): "720p",
    (854, 480): "480p",
    (480, 854): "480p",
}

# 短边下限 → 文案，从高到低
CLARITY_SHORT_SIDE: tuple[tuple[int, str], ...] = (
    (2160, "4K"),
    (1440, "1440p"),
    (1080, "1080p"),
    (720, "720p"),
    (480, "480p"),
)

EFFICIENT_CODECS: frozenset[str] = frozenset(
    {"hevc", "h265", "hev1", "hvc1", "av1", "av01", "vp9", "vp09"}
)
EFFICIENT_CODEC_BPP_WEIGHT = 1.6

# bpp 下限 → 文案，从高到低
QUALITY_BPP_LABELS: tuple[tuple[float, str], ...] = (
    (0.20, "高"),
    (0.10, "中"),
    (0.05, "一般"),
)
QUALITY_BPP_FALLBACK = "偏低"


def clarity_label(width: int | None, height: int | None) -> str | None:
    """分辨率档位；缺一维则空。竖屏按短边，避免只看 height 错档。"""
    if width is None or height is None or width <= 0 or height <= 0:
        return None
    pair = CLARITY_STANDARD.get((width, height))
    if pair is not None:
        return pair
    short = min(width, height)
    for threshold, label in CLARITY_SHORT_SIDE:
        if short >= threshold:
            return label
    return f"{short}p"


def quality_label(
    width: int | None,
    height: int | None,
    fps: float | None,
    bitrate: int | None,
    codec: str | None = None,
) -> str | None:
    """由 bpp 分档：高 / 中 / 一般 / 偏低。缺输入则空。"""
    if (
        width is None
        or height is None
        or fps is None
        or bitrate is None
        or width <= 0
        or height <= 0
        or fps <= 0
        or bitrate <= 0
    ):
        return None
    bpp = bitrate / (width * height * fps)
    name = (codec or "").lower().split(".")[0]
    if name in EFFICIENT_CODECS:
        bpp *= EFFICIENT_CODEC_BPP_WEIGHT
    for threshold, label in QUALITY_BPP_LABELS:
        if bpp >= threshold:
            return label
    return QUALITY_BPP_FALLBACK
