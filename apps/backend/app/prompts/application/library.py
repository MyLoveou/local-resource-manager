"""内置提示词库：读取抽取好的 JSON，拼成前端需要的一份载荷。

内置库是只读的（随版本升级替换），用户自建内容在 SQLite 里，两者不混。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read(name: str):
    path = DATA_DIR / name
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_tag_lines(blob: str) -> list[dict]:
    """`tags` 字段是 `en|zh` 的逐行文本。"""
    items: list[dict] = []
    for raw in (blob or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "|" in line:
            en, _, zh = line.partition("|")
        else:
            en, zh = line, ""
        en = en.strip()
        if not en:
            continue
        items.append({"en": en, "zh": zh.strip()})
    return items


@lru_cache(maxsize=1)
def library_payload() -> dict:
    categories = []
    for category in _read("tags.json"):
        categories.append(
            {
                "id": category.get("id", ""),
                "name": category.get("name", ""),
                "icon": category.get("icon", ""),
                "tags": _parse_tag_lines(category.get("tags", "")),
            }
        )

    characters = [
        {
            "game": item.get("game", ""),
            "gameTag": item.get("gameTag", ""),
            "name": item.get("name", ""),
            "tag": item.get("tag", ""),
            "charZh": item.get("charZh") or item.get("name", ""),
            "auto": item.get("auto", ""),
        }
        for item in _read("characters.json")
    ]

    presets = [
        {
            "name": item.get("name", ""),
            "desc": item.get("desc", ""),
            "cat": item.get("cat", ""),
            "tags": _parse_tag_lines((item.get("tags") or "").replace(";", "\n")),
        }
        for item in _read("presets.json")
    ]

    templates = [
        {
            "id": item.get("id", ""),
            "icon": item.get("icon", ""),
            "name": item.get("name", ""),
            "desc": item.get("desc", ""),
            "tags": _parse_tag_lines((item.get("tags") or "").replace(";", "\n")),
            "layout": item.get("layout"),
        }
        for item in _read("tpls.json")
    ]

    return {
        "models": _read("models.json"),
        "categories": categories,
        "characters": characters,
        "presets": presets,
        "templates": templates,
        "presetCategories": _read("preset_cats.json"),
        "presetCategoryMap": _read("preset_cat_map.json"),
        "charGroups": _read("char_groups.json"),
        "rules": _read("rules.json"),
        "pinyin": _read("pinyin.json"),
        "extraZh": _read("extra_zh.json"),
        "zhSynonym": _read("zh_synonym.json"),
    }


def reset_cache() -> None:
    library_payload.cache_clear()
