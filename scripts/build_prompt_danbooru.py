"""把 danbooru 标签表（danbooru-tag-list-zh 的 CSV）整理成内置库的一部分。

CSV 结构：tag,category,post_count,"aliases"
  category 0=general 1=artist 3=copyright 4=character 5=meta

做法：取 general 里使用量最高的 N 个，和现有内置标签的中文名合并，
并标记成人向词，供前端按开关过滤。

用法：python scripts/build_prompt_danbooru.py <csv> [数量]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

DATA = Path("apps/backend/app/prompts/data")

# 常见成人向词根，命中即在默认视图里隐藏
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


def is_nsfw(tag: str) -> bool:
    lowered = tag.lower()
    return any(hint in lowered for hint in NSFW_HINTS)


def main() -> int:
    csv_path = Path(sys.argv[1])
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

    zh: dict[str, str] = {}
    for category in json.loads((DATA / "tags.json").read_text(encoding="utf-8")):
        for line in (category.get("tags") or "").splitlines():
            if "|" in line:
                en, _, chinese = line.partition("|")
                zh[en.strip()] = chinese.strip()

    rows: list[tuple[str, int, list[str]]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 4:
                continue
            tag, category, count, aliases = row[0], row[1], row[2], row[3]
            if category != "0":
                continue
            try:
                uses = int(count)
            except ValueError:
                continue
            alias_list = [item.strip() for item in aliases.split(",") if item.strip()]
            rows.append((tag.strip(), uses, alias_list))

    rows.sort(key=lambda item: item[1], reverse=True)
    picked = rows[:limit]

    payload = [
        {
            "en": tag,
            "zh": zh.get(tag, ""),
            "count": uses,
            "aliases": aliases[:6],
            "nsfw": is_nsfw(tag) or any(is_nsfw(alias) for alias in aliases[:3]),
        }
        for tag, uses, aliases in picked
    ]

    out = DATA / "danbooru.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    nsfw_count = sum(1 for item in payload if item["nsfw"])
    print(f"写入 {out}: {len(payload)} 条（其中成人向 {nsfw_count} 条）")
    print(f"来源总量: {len(rows)} 条 general 标签，取前 {limit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
