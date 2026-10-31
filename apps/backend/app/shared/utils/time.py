"""SQLite 文本时间戳的单一转换点。

统一 ``datetime ↔ SQLite TEXT`` 的格式与转换，避免各仓储重复实现 ``_now/_ts``。
"""
from __future__ import annotations

from datetime import datetime

SQLITE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def db_now() -> str:
    """与 SQLite ``datetime('now')`` 同格式的当前时间戳。"""
    return datetime.now().strftime(SQLITE_TIME_FORMAT)


def db_ts(value: datetime | str | None) -> str | None:
    """领域 ``datetime`` / 已有字符串 → SQLite 文本列；``None`` 原样返回。"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.strftime(SQLITE_TIME_FORMAT)
