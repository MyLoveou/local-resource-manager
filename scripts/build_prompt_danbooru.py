"""把 danbooru 标签表整理成内置库：通用 / 画师 / 角色 三类。

CSV 结构：tag,category,post_count,"aliases"
  category 0=general 1=artist 3=copyright 4=character 5=meta

用法：python scripts/build_prompt_danbooru.py <csv> [每类数量]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

DATA = Path("apps/backend/app/prompts/data")

CATEGORIES = {"0": "general", "1": "artist", "3": "copyright", "4": "character", "5": "meta"}

NSFW_HINTS = {
    "nude", "naked", "nipple", "nipples", "pussy", "penis", "sex", "cum", "semen",
    "anal", "oral", "fellatio", "cunnilingus", "masturbation", "orgasm", "ejaculation",
    "topless", "bottomless", "underwear", "panties", "bra", "lingerie", "bikini",
    "cleavage", "large breasts", "huge breasts", "gigantic breasts", "flat chest",
    "small breasts", "medium breasts", "areola", "pubic hair", "uncensored", "censored",
    "bondage", "bdsm", "ahegao", "spread legs", "spread pussy", "sex from behind",
    "paizuri", "futanari", "loli", "shota", "nsfw", "explicit", "sensitive",
    "erection", "crotch", "thigh gap", "ass", "butt", "booty", "upskirt", "see-through",
    "wet clothes", "humping", "grinding", "tentacle", "tentacles", "monster girl",
}


BANNED_PREFIX = ("banned_", "unknown_", "artist_request", "third-party_edit",
                 "bad_", "tag_", "commentary_request")


def is_junk(name: str, category: str) -> bool:
    """画师/角色里混着站点维护用的伪标签，直接丢掉。"""
    if category == "general":
        return False
    lowered = name.lower()
    return any(lowered.startswith(prefix) for prefix in BANNED_PREFIX)


def is_nsfw(tag: str) -> bool:
    lowered = tag.lower()
    return any(hint in lowered for hint in NSFW_HINTS)


def main() -> int:
    csv_path = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    wanted = {"general", "artist", "character"}

    zh: dict[str, str] = {}
    for category in json.loads((DATA / "tags.json").read_text(encoding="utf-8")):
        for line in (category.get("tags") or "").splitlines():
            if "|" in line:
                en, _, chinese = line.partition("|")
                zh[en.strip()] = chinese.strip()

    buckets: dict[str, list[tuple[str, int, list[str]]]] = {key: [] for key in wanted}
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 4:
                continue
            tag, code, count, aliases = row[0].strip(), row[1], row[2], row[3]
            name = CATEGORIES.get(code)
            if name not in wanted or not tag:
                continue
            try:
                uses = int(count)
            except ValueError:
                continue
            if is_junk(tag, name):
                continue
            alias_list = [item.strip() for item in aliases.split(",") if item.strip()]
            buckets[name].append((tag, uses, alias_list))

    payload: list[dict] = []
    for name, rows in buckets.items():
        rows.sort(key=lambda item: item[1], reverse=True)
        for tag, uses, aliases in rows[:limit]:
            payload.append(
                {
                    "en": tag,
                    "zh": zh.get(tag, ""),
                    "count": uses,
                    "aliases": aliases[:4],
                    "nsfw": is_nsfw(tag) or any(is_nsfw(alias) for alias in aliases[:2]),
                    "cat": name,
                }
            )

    out = DATA / "danbooru.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    stats = {name: sum(1 for item in payload if item["cat"] == name) for name in buckets}
    print(f"写入 {out}: {len(payload)} 条")
    print(f"分类: {stats}")
    print(f"成人向: {sum(1 for item in payload if item['nsfw'])} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
