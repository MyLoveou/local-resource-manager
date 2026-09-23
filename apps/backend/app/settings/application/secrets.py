"""刮削凭证：环境变量优先，否则 settings KV。"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from app.shared.config import settings
from app.shared.infrastructure.settings_repo import KEY_BANGUMI, KEY_MIKAN, KEY_TMDB

DEFAULT_MIKAN = "https://mikanani.kas.pub"

_cache: dict[str, dict] = {}
_loaded = False


def invalidate_secret_cache() -> None:
    global _loaded
    _loaded = False
    _cache.clear()


def remember(key: str, value: dict) -> None:
    _cache[key] = dict(value)
    global _loaded
    _loaded = True


def env_tmdb_key() -> str:
    return (os.environ.get("TMDB_API_KEY") or "").strip()


def env_bangumi_token() -> str:
    return (os.environ.get("BANGUMI_ACCESS_TOKEN") or "").strip()


def env_mikan_base() -> str:
    return (os.environ.get("MIKAN_BASE_URL") or "").strip().rstrip("/")


def tmdb_api_key() -> str:
    env = env_tmdb_key()
    if env:
        return env
    blob = _kv(KEY_TMDB)
    return str(blob.get("apiKey") or "").strip()


def bangumi_token() -> str:
    env = env_bangumi_token()
    if env:
        return env
    blob = _kv(KEY_BANGUMI)
    return str(blob.get("accessToken") or "").strip()


def mikan_base_url() -> str:
    env = env_mikan_base()
    if env:
        return env
    blob = _kv(KEY_MIKAN)
    stored = str(blob.get("baseUrl") or "").strip().rstrip("/")
    return stored or DEFAULT_MIKAN


def _kv(key: str) -> dict:
    _ensure_loaded()
    data = _cache.get(key) or {}
    return data if isinstance(data, dict) else {}


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    path = Path(settings.db_path)
    if not path.is_file():
        _loaded = True
        return
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'scrape.%'").fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        _loaded = True
        return
    for key, raw in rows:
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            _cache[str(key)] = data
    _loaded = True
