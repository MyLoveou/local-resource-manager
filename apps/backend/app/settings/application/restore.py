"""Safe two-phase restore from a full backup ZIP."""

from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from app.library.application.packages.resource_package import default_library_store
from app.shared.log import logger
from app.settings.application.errors import SettingsError

PENDING_DIR = "restore-pending"
MANIFEST = "restore.json"


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and not name.startswith("\\")


def prepare_restore(db_path: Path, source: Path) -> Path:
    archive = source.expanduser().resolve()
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        raise SettingsError("请选择有效的 ZIP 备份文件", 400)
    pending = db_path.parent / PENDING_DIR
    if pending.exists():
        shutil.rmtree(pending)
    pending.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
            if "library.db" not in names:
                raise SettingsError("备份缺少 library.db", 400)
            if any(not _safe_member(name) for name in names):
                raise SettingsError("备份包含不安全路径", 400)
            zipped.extractall(pending)
        restored_db = pending / "library.db"
        conn = sqlite3.connect(str(restored_db))
        try:
            check = conn.execute("PRAGMA integrity_check").fetchone()
            if not check or check[0] != "ok":
                raise SettingsError("备份数据库完整性检查失败", 400)
        finally:
            conn.close()
        manifest = {
            "source": str(archive),
            "db_path": str(db_path.resolve()),
            "library_path": str(default_library_store(db_path).resolve()),
            "prepared_at": datetime.now().isoformat(timespec="seconds"),
        }
        (pending / MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("restore prepared source=%s pending=%s", archive, pending)
        return pending
    except Exception:
        shutil.rmtree(pending, ignore_errors=True)
        raise


def _update_library_setting(db_path: Path, library: Path) -> None:
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'system'"
        ).fetchone()
        data = json.loads(row[0]) if row and row[0] else {}
        if not isinstance(data, dict):
            data = {}
        data["library_path"] = str(library)
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('system', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (json.dumps(data, ensure_ascii=False),),
        )
        conn.commit()
        conn.close()
    except (OSError, sqlite3.Error, ValueError):
        logger.exception("failed to update restored library setting")


def apply_pending_restore(db_path: Path) -> bool:
    pending = db_path.parent / PENDING_DIR
    if not pending.is_dir():
        return False
    manifest_path = pending / MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        shutil.rmtree(pending, ignore_errors=True)
        return False
    restored_db = pending / "library.db"
    if not restored_db.is_file():
        shutil.rmtree(pending, ignore_errors=True)
        return False
    library = Path(str(manifest.get("library_path") or default_library_store(db_path)))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    old_db = db_path.with_name(f"{db_path.stem}.restore-old-{stamp}{db_path.suffix}")
    old_library = library.with_name(f"{library.name}.restore-old-{stamp}")
    moved_db = False
    moved_library = False
    try:
        for suffix in ("-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)
        if db_path.exists():
            shutil.move(str(db_path), str(old_db))
            moved_db = True
        if library.exists():
            shutil.move(str(library), str(old_library))
            moved_library = True
        shutil.copy2(restored_db, db_path)
        restored_library = pending / "library"
        if restored_library.is_dir():
            shutil.copytree(restored_library, library)
        else:
            library.mkdir(parents=True, exist_ok=True)
        _update_library_setting(db_path, library)
        shutil.rmtree(pending, ignore_errors=True)
        logger.info("restore applied source=%s", manifest.get("source"))
        return True
    except Exception:
        logger.exception("restore apply failed; attempting rollback")
        db_path.unlink(missing_ok=True)
        if moved_db and old_db.exists():
            shutil.move(str(old_db), str(db_path))
        if moved_library and old_library.exists():
            shutil.rmtree(library, ignore_errors=True)
            shutil.move(str(old_library), str(library))
        raise
