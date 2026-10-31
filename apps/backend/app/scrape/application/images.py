"""刮削图片 URL：https 化 + 精确域名白名单。"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx

_POSTER_HOSTS = frozenset(
    {
        "image.tmdb.org",
        "lain.bgm.tv",
        "i0.hdslb.com",
        "i1.hdslb.com",
        "i2.hdslb.com",
        "i3.hdslb.com",
        "i4.hdslb.com",
        "s1.hdslb.com",
        "mikanani.kas.pub",
        "mikanani.me",
        "www.mikanani.me",
        "mikanime.tv",
        "www.mikanime.tv",
    }
)
_MAX_BYTES = 8 * 1024 * 1024
POSTER_HEADERS = {"User-Agent": "SourceManager/0.1 (local library; metadata scrape)"}


def normalize_https(url: str | None) -> str | None:
    if not url:
        return None
    text = url.strip()
    if not text:
        return None
    if text.startswith("//"):
        text = "https:" + text
    if text.startswith("http://"):
        text = "https://" + text[len("http://") :]
    return text


def allowed_poster(url: str | None) -> bool:
    normalized = normalize_https(url)
    if not normalized:
        return False
    parsed = urlparse(normalized)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return host in _POSTER_HOSTS


def public_image_url(url: str | None) -> str | None:
    """已知封面站走白名单；其余 https 须通过与下载相同的公网校验。"""
    normalized = normalize_https(url)
    if not normalized:
        return None
    if allowed_poster(normalized):
        return normalized
    from app.shared.errors import DownloadError
    from app.shared.utils.ssrf import validate_http_url

    try:
        validate_http_url(normalized)
    except DownloadError:
        return None
    return normalized


def unique_https(urls: list[str | None]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in urls:
        item = public_image_url(raw)
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def sniff_image(content: bytes) -> str | None:
    if len(content) < 12:
        return None
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


async def fetch_poster_bytes(url: str) -> tuple[bytes, str]:
    target = public_image_url(url)
    if not target:
        raise RuntimeError("封面地址不允许")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False, headers=POSTER_HEADERS) as client:
        current = target
        for _ in range(5):
            async with client.stream("GET", current) as res:
                if res.status_code in {301, 302, 303, 307, 308}:
                    loc = res.headers.get("location")
                    if not loc:
                        raise RuntimeError("封面跳转不允许")
                    nxt = public_image_url(urljoin(current, loc))
                    if not nxt:
                        raise RuntimeError("封面跳转不允许")
                    current = nxt
                    continue
                res.raise_for_status()
                body = bytearray()
                async for chunk in res.aiter_bytes(64 * 1024):
                    if len(body) + len(chunk) > _MAX_BYTES:
                        raise RuntimeError("封面过大")
                    body.extend(chunk)
                mime = sniff_image(bytes(body))
                if mime is None:
                    raise RuntimeError("封面不是图片")
                return bytes(body), mime
        raise RuntimeError("封面跳转过多")
