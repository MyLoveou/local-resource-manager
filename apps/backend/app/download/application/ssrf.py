"""拒绝非 HTTP(S) 与解析到私网的下载 URL。"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.download.application.errors import DownloadError


def validate_http_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise DownloadError("请填写下载地址", 400)
    lowered = text.lower()
    if lowered.startswith("magnet:"):
        raise DownloadError("本刀仅支持 HTTP(S) 直链", 400)
    if lowered.startswith("file:"):
        raise DownloadError("不支持本地文件地址", 400)
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise DownloadError("仅支持 HTTP(S) 直链", 400)
    if parsed.username or parsed.password:
        raise DownloadError("地址不能包含账号信息", 400)
    host = (parsed.hostname or "").strip().rstrip(".")
    if not host:
        raise DownloadError("地址缺少主机名", 400)
    _assert_public_host(host)
    return text


def require_public_host(host: str) -> None:
    _assert_public_host(host)


def _assert_public_host(host: str) -> None:
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _blocked_ip(literal):
            raise DownloadError("不允许下载内网或本机地址", 400)
        return
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise DownloadError("无法解析主机", 400) from exc
    if not infos:
        raise DownloadError("无法解析主机", 400)
    for info in infos:
        packed = info[4][0]
        ip = ipaddress.ip_address(packed)
        if _blocked_ip(ip):
            raise DownloadError("不允许下载内网或本机地址", 400)


def _blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
