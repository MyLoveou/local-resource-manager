"""Repair WD14 AI documents whose display labels were stored as question marks."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from app.ai.infrastructure.anime_tagger import MODEL_ID, TAG_ZH


def repair(path: Path, apply: bool) -> tuple[int, int]:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT resource_id, caption, short_caption, tags_json, attributes_json "
        "FROM ai_documents WHERE model_id = ?",
        (MODEL_ID,),
    ).fetchall()
    changed = 0
    for row in rows:
        try:
            attrs = json.loads(row["attributes_json"] or "{}")
        except ValueError:
            continue
        raw_tags = [str(item) for item in (attrs.get("tags") or []) if str(item).strip()]
        if not raw_tags:
            continue
        display = [TAG_ZH.get(tag, tag) for tag in raw_tags]
        caption = "动漫插画，" + "，".join(display[:8])
        short = "，".join(display[:3])
        if display == json.loads(row["tags_json"] or "[]") and caption == row["caption"]:
            continue
        changed += 1
        if not apply:
            print(f"would repair resource={row['resource_id']} tags={display}")
            continue
        attrs["display_tags"] = display
        conn.execute(
            "UPDATE ai_documents SET caption = ?, short_caption = ?, "
            "tags_json = ?, attributes_json = ?, updated_at = datetime('now') "
            "WHERE resource_id = ?",
            (
                caption,
                short,
                json.dumps(display, ensure_ascii=False),
                json.dumps(attrs, ensure_ascii=False),
                row["resource_id"],
            ),
        )
        conn.execute(
            "DELETE FROM ai_tags WHERE resource_id = ? AND source = 'wd14'",
            (row["resource_id"],),
        )
        for tag in dict.fromkeys(display):
            conn.execute(
                "INSERT OR IGNORE INTO ai_tags "
                "(resource_id, tag, category, confidence, source, model_id) "
                "VALUES (?, ?, NULL, NULL, 'wd14', ?)",
                (row["resource_id"], tag, MODEL_ID),
            )
    if apply:
        conn.commit()
    conn.close()
    return len(rows), changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    total, changed = repair(args.db, args.apply)
    print(f"wd14_documents={total} changed={changed} applied={args.apply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
