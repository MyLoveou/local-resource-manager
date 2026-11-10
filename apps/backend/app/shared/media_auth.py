"""Short-lived, path-bound media URL signatures.

Media elements (img/video/audio/model-viewer) cannot send an Authorization
header, so their URLs carry an expiry and HMAC signature instead. The HMAC key
is the per-launch backend token; unsigned media URLs are rejected when auth is
enabled.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from app.shared.config import settings

MEDIA_TTL_SECONDS = 3600


def _key() -> bytes:
    return (settings.token or "dev-media").encode("utf-8")


def _signature(path: str, expires: int) -> str:
    message = f"{path}:{expires}".encode("utf-8")
    return hmac.new(_key(), message, hashlib.sha256).hexdigest()


def sign_media_path(path: str | None) -> str | None:
    """Return a signed local media path, or the original path when auth is off."""
    if not path:
        return path
    if not settings.token:
        return path
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc:
        return path
    if not parsed.path.startswith("/library/"):
        return path
    expires = int(time.time()) + MEDIA_TTL_SECONDS
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["exp"] = [str(expires)]
    query["sig"] = [_signature(parsed.path, expires)]
    return urlunsplit(("", "", parsed.path, urlencode(query, doseq=True), ""))


def verify_media_path(path: str, expires: str | None, signature: str | None) -> bool:
    if not settings.token or not expires or not signature:
        return not settings.token
    try:
        expires_at = int(expires)
    except ValueError:
        return False
    if expires_at < int(time.time()):
        return False
    expected = _signature(path, expires_at)
    return hmac.compare_digest(expected, signature)


def unsigned_media_path(path: str | None) -> str | None:
    """Strip a media signature before persisting a URL back to the database."""
    if not path:
        return path
    parsed = urlsplit(path)
    query = parse_qs(parsed.query, keep_blank_values=True)
    if "exp" not in query and "sig" not in query:
        return path
    return urlunsplit(("", "", parsed.path, "", ""))
