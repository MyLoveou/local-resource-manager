"""0018 旧扁平分类迁移：按类型复制、资源关系与待整理分类。"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.shared.db.db import _apply_sqlite_pragmas
from app.shared.db.migrations import MIGRATIONS_DIR, migrate


class CategoryMigrationTests(unittest.TestCase):
    def test_legacy_categories_are_copied_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.db"
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            _apply_sqlite_pragmas(conn)
            conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL PRIMARY KEY)")
            for sql_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                version = int(sql_path.name.split("_", 1)[0])
                if version > 17:
                    continue
                conn.executescript(sql_path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))
            conn.execute("INSERT INTO categories(id, name) VALUES (1, 'A')")
            conn.execute("INSERT INTO categories(id, name) VALUES (2, 'B')")
            conn.execute("INSERT INTO categories(id, name) VALUES (3, 'C')")
            for rid, type_, cat in [(1, "image", 1), (2, "video", 1), (3, "image", 2)]:
                conn.execute(
                    "INSERT INTO resources(id, type, title, status, extra, storage_kind, category_id) "
                    "VALUES (?, ?, ?, 'active', '{}', 'owned', ?)",
                    (rid, type_, f"r{rid}", cat),
                )
            conn.commit()
            expected = sum(
                1
                for path in MIGRATIONS_DIR.glob("*.sql")
                if int(path.name.split("_", 1)[0]) > 17
            )
            self.assertEqual(migrate(conn), expected)

            categories = {
                (row["type"], row["name"]): row["id"]
                for row in conn.execute("SELECT id,type,name FROM categories")
            }
            self.assertIn(("image", "A"), categories)
            self.assertIn(("video", "A"), categories)
            self.assertIn(("image", "B"), categories)
            self.assertIn(("image", "C"), categories)
            self.assertNotIn(("video", "C"), categories)

            pending = categories[("image", "待整理分类")]
            orphan = conn.execute(
                "SELECT parent_id FROM categories WHERE type='image' AND name='C'"
            ).fetchone()
            self.assertEqual(orphan["parent_id"], pending)

            memberships = {
                (row["resource_id"], row["category_id"])
                for row in conn.execute("SELECT resource_id, category_id FROM resource_categories")
            }
            self.assertIn((1, categories[("image", "A")]), memberships)
            self.assertIn((2, categories[("video", "A")]), memberships)
            self.assertIn((3, categories[("image", "B")]), memberships)
            self.assertEqual(len(memberships), 3)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            conn.close()


if __name__ == "__main__":
    unittest.main()
