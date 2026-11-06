"""生成 SQLite 在线快照，供 GitMove 修订记录。

用 sqlite3 的 backup API 而不是直接拷文件：WAL 模式下直接复制可能拿到半状态。
用法：
    apps/backend/.venv/Scripts/python.exe scripts/db-snapshot.py
输出：snapshots/library-<时间戳>.db
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps" / "backend" / "data" / "library.db"
TARGET_DIR = ROOT / "snapshots"


def main() -> int:
    if not SOURCE.is_file():
        print(f"源数据库不存在：{SOURCE}")
        return 1
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = TARGET_DIR / f"library-{stamp}.db"

    source = sqlite3.connect(f"file:{SOURCE}?mode=ro", uri=True, timeout=30)
    dest = sqlite3.connect(target)
    try:
        source.backup(dest)
        version = dest.execute("select max(version) from schema_version").fetchone()[0]
    finally:
        dest.close()
        source.close()

    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"快照：{target.relative_to(ROOT)}   schema={version}   {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
