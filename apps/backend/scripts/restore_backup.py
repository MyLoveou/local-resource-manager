"""Restore a full ZIP backup created by the settings backup action.

Stop the desktop app before running this script. It creates a safety backup of
the current database/library first, then replaces them from the archive.

Usage (from apps/backend):
  .venv\\Scripts\\python scripts/restore_backup.py D:\\backup\\library-....zip --yes
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.library.application.packages.resource_package import default_library_store  # noqa: E402
from app.settings.application.service import backup_library  # noqa: E402
from app.shared.config import settings  # noqa: E402
from app.shared.runtime_paths import set_library_root  # noqa: E402


def _stored_library_root(db_path: Path) -> Path:
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'system'"
        ).fetchone()
        conn.close()
        if row and row[0]:
            data = json.loads(row[0])
            value = data.get("library_path") if isinstance(data, dict) else None
            if isinstance(value, str) and value.strip():
                return Path(value).resolve()
    except (OSError, sqlite3.Error, json.JSONDecodeError):
        pass
    return default_library_store(db_path)


def _validate_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError("backup database integrity check failed")
    finally:
        conn.close()


def restore(zip_path: Path, apply: bool) -> int:
    source = zip_path.resolve()
    if not source.is_file():
        print(f"backup not found: {source}")
        return 1
    db_path = settings.db_path.resolve()
    library = _stored_library_root(db_path)
    set_library_root(library)
    with tempfile.TemporaryDirectory(prefix="source-manager-restore-") as tmp:
        temp = Path(tmp)
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            if "library.db" not in names:
                print("invalid backup: library.db missing")
                return 1
            archive.extractall(temp)
        restored_db = temp / "library.db"
        _validate_db(restored_db)
        restored_library = temp / "library"
        if not apply:
            print(f"would restore {source}")
            print(f"db: {db_path}")
            print(f"library: {library}")
            return 0

        safety = backup_library(db_path)
        print(f"safety backup: {safety.path}")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if library.exists():
            old_library = library.with_name(f"{library.name}.old-{stamp}")
            library.rename(old_library)
            print(f"old library moved to: {old_library}")
        if restored_library.is_dir():
            shutil.copytree(restored_library, library)
        shutil.copy2(restored_db, db_path)
        set_library_root(library)
        print(f"restored: {db_path}")
        print(f"library: {library}")
        print("restart the desktop app now")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="restore a full library backup")
    parser.add_argument("backup", type=Path)
    parser.add_argument("--yes", action="store_true", help="apply the restore")
    args = parser.parse_args()
    if not args.yes:
        print("dry-run; pass --yes to restore (stop the desktop app first)")
    return restore(args.backup, args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
