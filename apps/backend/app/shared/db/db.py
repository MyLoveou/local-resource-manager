"""SQLite 连接管理（SQLAlchemy 2.0 async + aiosqlite）。

- 迁移仍用同步 sqlite3（init_db）
- 业务读写经 AsyncSession（get_session）
"""
import sqlite3
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.config import settings
from app.shared.db.migrations import migrate

_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _database_url(db_path: Path | None = None) -> str:
    path = (db_path or settings.db_path).resolve()
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def _apply_sqlite_pragmas(dbapi_conn: sqlite3.Connection) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    # 单机读多写少：NORMAL 比 FULL 少 fsync；负值 cache_size 为 KiB
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-8000")
    cursor.close()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """同步连接（仅迁移 / init_db 使用）。"""
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _apply_sqlite_pragmas(conn)
    return conn


def get_engine():
    """懒加载 async engine。"""
    global _engine, _async_session_factory
    if _engine is None:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(
            _database_url(),
            echo=False,
        )

        @event.listens_for(_engine.sync_engine, "connect")
        def _on_connect(dbapi_conn, _connection_record) -> None:
            _apply_sqlite_pragmas(dbapi_conn)

        _async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _async_session_factory is not None
    return _async_session_factory


def database_file_ready(db_path: Path | None = None) -> bool:
    """库文件已存在且非空（失败中断留下的 0 字节文件视为未创建）。"""
    path = (db_path or settings.db_path).resolve()
    return path.is_file() and path.stat().st_size > 0


def ensure_db() -> bool:
    """无库文件则创建并迁移；已有文件则只连接（并补跑未应用的迁移）。

    返回 True 表示本次新建了库文件。
    """
    is_new = not database_file_ready()
    if is_new:
        init_db()
        return True
    _apply_pending_migrations()
    return False


def _apply_pending_migrations() -> int:
    conn = connect()
    try:
        return migrate(conn)
    finally:
        conn.close()


def init_db() -> None:
    """创建库文件并执行迁移（仅首次）。"""
    conn = connect()
    try:
        migrate(conn)
    finally:
        conn.close()


async def dispose_engine() -> None:
    """关闭 async engine（应用退出时）。"""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：每请求一个 AsyncSession。"""
    factory = get_session_factory()
    async with factory() as session:
        yield session
