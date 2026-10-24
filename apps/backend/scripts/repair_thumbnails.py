"""补生成缺失缩略图；默认只补不删，删除资源必须显式指定。

用法（在 apps/backend）：
  .venv\\Scripts\\python scripts/repair_thumbnails.py --apply
  .venv\\Scripts\\python scripts/repair_thumbnails.py --apply --delete-unrepairable
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.library.application.packages.resource_package import (  # noqa: E402
    ResourcePackage,
    default_library_store,
)
from app.library.application.packages.layouts import layout_for  # noqa: E402
from app.library.application.thumbnails import source_for_grid_thumbnail  # noqa: E402
from app.library.application.use_cases import LibraryQueryService  # noqa: E402
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository  # noqa: E402
from app.shared.config import settings  # noqa: E402
from app.shared.db.migrations import migrate  # noqa: E402
from app.shared.fs.file_ops import FileOps  # noqa: E402
from app.library.domain.media_types import FILE_ROLE_THUMBNAIL  # noqa: E402
import sqlite3  # noqa: E402


async def _repair(*, apply: bool, delete_unrepairable: bool = False) -> int:
    db_path = settings.db_path.resolve()
    if not db_path.is_file():
        print(f"无库文件: {db_path}")
        return 0
    conn = sqlite3.connect(str(db_path))
    migrate(conn)
    conn.close()
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    store = default_library_store(db_path)
    ops = FileOps()
    deleted = 0
    repaired = 0
    skipped = 0
    ok = 0
    async with factory() as session:
        resources = ResourceRepository(session)
        svc = LibraryQueryService(resources, TaskSummaryRepository(session), file_ops=ops, store_root=store)
        ids = await resources.list_resource_ids()
        for rid in ids:
            row = await resources.get(rid)
            if row is None or row.id is None:
                continue
            thumb = next((f for f in row.files if f.role == FILE_ROLE_THUMBNAIL), None)
            if thumb is not None and Path(thumb.path).is_file():
                ok += 1
                continue
            role_paths = {f.role or "": Path(f.path) for f in row.files if f.path}
            src = source_for_grid_thumbnail(row.type, role_paths)
            layout = layout_for(row.type)
            package = ResourcePackage(
                store,
                row.type,
                row.id,
                ops,
                cover_falls_back_to_primary=layout.cover_falls_back_to_primary if layout else True,
            )
            dest = None
            if src is not None and src.is_file():
                dest = await asyncio.to_thread(package.put_thumbnail, src)
            if dest is not None and dest.is_file():
                if not apply:
                    print(f"would repair {rid}")
                    repaired += 1
                    continue
                size = dest.stat().st_size
                if thumb is not None:
                    await resources.update_file_stat(
                        thumb.id,
                        path=str(dest),
                        size=size,
                        format_=dest.suffix.lower().lstrip("."),
                        commit=True,
                    )
                else:
                    await resources.add_file(
                        rid,
                        path=str(dest),
                        sha256=None,
                        size=size,
                        format_=dest.suffix.lower().lstrip("."),
                        role=FILE_ROLE_THUMBNAIL,
                        commit=True,
                    )
                repaired += 1
                print(f"repaired {rid}")
                continue
            if not delete_unrepairable:
                skipped += 1
                print(f"skip {rid}: thumbnail unavailable (resource kept)")
                continue
            if not apply:
                print(f"would delete {rid}")
                deleted += 1
                continue
            await svc.purge(rid)
            deleted += 1
            print(f"deleted {rid}")
    await engine.dispose()
    print(f"ok={ok} repaired={repaired} skipped={skipped} deleted={deleted}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="repair missing grid thumbnails")
    parser.add_argument("--apply", action="store_true", help="write repaired thumbnails")
    parser.add_argument(
        "--delete-unrepairable",
        action="store_true",
        help="dangerous: purge resources whose thumbnail cannot be rebuilt",
    )
    args = parser.parse_args()
    print(f"db: {settings.db_path.resolve()}")
    if not args.apply:
        print("dry-run; pass --apply to write changes")
    if args.delete_unrepairable and not args.apply:
        print("--delete-unrepairable ignored without --apply")
    return asyncio.run(
        _repair(
            apply=args.apply,
            delete_unrepairable=args.delete_unrepairable and args.apply,
        )
    )



if __name__ == "__main__":
    raise SystemExit(main())
