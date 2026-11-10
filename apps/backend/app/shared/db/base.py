"""SQLAlchemy ORM 基类（对齐 migrations/*.sql，仅 DB 层）。"""
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

_SQLITE_NOW = text("(datetime('now'))")


class Base(DeclarativeBase):
    """ORM 基类。"""
