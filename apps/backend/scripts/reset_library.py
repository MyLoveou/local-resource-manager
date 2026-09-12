"""清空 SQLite 与库目录。须先退出桌面应用。

用法（在 apps/backend）：
  .venv\\Scripts\\python scripts/reset_library.py --yes
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.library.application.packages.resource_package import default_library_store  # noqa: E402
from app.shared.config import settings  # noqa: E402


def _sidecars(db_path: Path) -> list[Path]:
    return [
        db_path,
        Path(str(db_path) + "-wal"),
        Path(str(db_path) + "-shm"),
        db_path.with_suffix(".db-wal"),
        db_path.with_suffix(".db-shm"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="删除当前库文件与 library/ 目录")
    parser.add_argument("--yes", action="store_true", help="确认删除")
    args = parser.parse_args()
    db_path = settings.db_path.resolve()
    store = default_library_store(db_path).resolve()
    print(f"db: {db_path}")
    print(f"store: {store}")
    if not args.yes:
        print("未加 --yes，不删除。")
        return 2
    for path in _sidecars(db_path):
        if path.is_file():
            path.unlink()
            print(f"deleted {path}")
    if store.is_dir():
        shutil.rmtree(store)
        print(f"deleted {store}")
    print("下次启动会新建空库并跑迁移。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
