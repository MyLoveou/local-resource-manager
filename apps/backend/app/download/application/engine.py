"""httpx 流式写盘；Range 续传。"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx

from app.download.application.errors import DownloadError
from app.download.application.ssrf import validate_http_url
from app.library.domain.type_profile import VIDEO_EXTENSIONS

_HEADERS = {
    "User-Agent": "Mozilla/5.0 SourceManager-download",
    "Accept": "*/*",
}
_CHUNK = 64 * 1024
_MAX_REDIRECTS = 5
_HTML_PREFIXES = (b"<", b"<!DOCTYPE", b"<html", b"<HTML")


def safe_filename(name: str) -> str:
    stem = Path(unquote(name)).name.replace("\\", "_").replace("/", "_")
    for char in '<>:"|?*':
        stem = stem.replace(char, "_")
    stem = stem.strip().strip(".")
    return stem or "video.mp4"


def extension_of(name: str) -> str:
    return Path(name).suffix.lower()


def is_video_name(name: str) -> bool:
    return extension_of(name) in VIDEO_EXTENSIONS


def filename_from_url(url: str) -> str | None:
    path = unquote(urlparse(url).path or "")
    name = Path(path).name
    if not name or name in (".", "/"):
        return None
    return safe_filename(name)


def filename_from_disposition(header: str | None) -> str | None:
    if not header:
        return None
    starred = re.search(r"filename\*=(?:UTF-8''|utf-8'')([^;]+)", header, re.I)
    if starred:
        return safe_filename(unquote(starred.group(1).strip().strip('"')))
    plain = re.search(r'filename="?([^";]+)"?', header, re.I)
    if plain:
        return safe_filename(plain.group(1).strip())
    return None


class StreamResult:
    def __init__(self, path: Path, filename: str, downloaded: int, total: int | None) -> None:
        self.path = path
        self.filename = filename
        self.downloaded = downloaded
        self.total = total


async def stream_to_file(
    url: str,
    dest: Path,
    *,
    resume_from: int = 0,
    on_progress: Callable[[int, int | None, int], Awaitable[None]] | None = None,
    should_abort: Callable[[], Awaitable[str | None]] | None = None,
    client: httpx.AsyncClient | None = None,
) -> StreamResult:
    own = client is None
    http = client or httpx.AsyncClient(timeout=60.0, follow_redirects=False, headers=_HEADERS)
    try:
        final_url, response = await _open_stream(http, url, resume_from)
        try:
            _reject_html(response)
            name = (
                filename_from_disposition(response.headers.get("content-disposition"))
                or filename_from_url(final_url)
                or dest.name
            )
            name = safe_filename(name)
            if not is_video_name(name):
                raise DownloadError("本刀仅视频", 400)
            total = _total_bytes(response, resume_from)
            dest.parent.mkdir(parents=True, exist_ok=True)
            mode = "ab" if resume_from > 0 and response.status_code == 206 else "wb"
            if mode == "wb":
                resume_from = 0
            downloaded = resume_from
            started = time.monotonic()
            first = True
            with dest.open(mode) as handle:
                async for chunk in response.aiter_bytes(_CHUNK):
                    if first:
                        first = False
                        if _looks_html(chunk):
                            raise DownloadError("不是可下载的文件", 400)
                    handle.write(chunk)
                    downloaded += len(chunk)
                    elapsed = max(0.001, time.monotonic() - started)
                    speed = int((downloaded - resume_from) / elapsed)
                    if on_progress is not None:
                        await on_progress(downloaded, total, speed)
                    if should_abort is not None:
                        signal = await should_abort()
                        if signal:
                            raise DownloadAbort(signal)
            if downloaded <= resume_from:
                raise DownloadError("空文件", 400)
            return StreamResult(dest, name, downloaded, total)
        finally:
            await response.aclose()
    finally:
        if own:
            await http.aclose()


class DownloadAbort(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.gid: str | None = None


async def _open_stream(
    http: httpx.AsyncClient,
    url: str,
    resume_from: int,
) -> tuple[str, httpx.Response]:
    current = validate_http_url(url)
    for _ in range(_MAX_REDIRECTS + 1):
        headers = dict(_HEADERS)
        if resume_from > 0:
            headers["Range"] = f"bytes={resume_from}-"
        request = http.build_request("GET", current, headers=headers)
        response = await http.send(request, stream=True)
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                raise DownloadError("跳转缺少地址", 400)
            current = validate_http_url(urljoin(current, location))
            continue
        if response.status_code in {200, 206}:
            return current, response
        await response.aclose()
        raise DownloadError(f"下载失败 HTTP {response.status_code}", 502)
    raise DownloadError("跳转次数过多", 400)


def _total_bytes(response: httpx.Response, resume_from: int) -> int | None:
    if response.status_code == 206:
        content_range = response.headers.get("content-range") or ""
        match = re.search(r"/(\d+)\s*$", content_range)
        if match:
            return int(match.group(1))
    length = response.headers.get("content-length")
    if not length or not length.isdigit():
        return None
    size = int(length)
    if response.status_code == 206:
        return resume_from + size
    return size


def _reject_html(response: httpx.Response) -> None:
    ctype = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype in {"text/html", "application/xhtml+xml"}:
        raise DownloadError("不是可下载的文件", 400)


def _looks_html(chunk: bytes) -> bool:
    head = chunk.lstrip()[:32]
    return any(head.startswith(prefix) for prefix in _HTML_PREFIXES)
