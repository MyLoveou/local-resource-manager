"""SQLite 连接管理。

- WAL 模式 + foreign_keys + busy_timeout
- 启动时执行迁移（init_db）
- FastAPI 依赖 get_connection（每请求一连接）
"""
import sqlite3
from collections.abc import Generator
from pathlib import Path

from app.shared.config import settings
from app.shared.db.migrations import migrate


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """建立连接并启用并发/完整性设置。"""
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> None:
    """初始化数据库并执行未应用的迁移（应用启动时调用）。"""
    conn = connect()
    try:
        migrate(conn)
    finally:
        conn.close()


def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI 依赖：每请求一个短连接，用后即关。"""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
