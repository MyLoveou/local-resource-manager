"""内置提示词库：读取抽取好的 JSON，拼成前端需要的一份载荷。

内置库是只读的（随版本升级替换），用户自建内容在 SQLite 里，两者不混。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LIBRARY_VERSION = 1


def external_path() -> Path:
    """用户导入的内置库文件；安装包不带数据时靠它。"""
    from app.shared.config import settings

    return settings.db_path.resolve().parent / "prompt-library.json"


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


def _bundled_available() -> bool:
    return (DATA_DIR / "tags.json").is_file()


def is_available() -> bool:
    return external_path().is_file() or _bundled_available()


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

    external = external_path()
    if external.is_file():
        import json as _json

        payload = _json.loads(external.read_text(encoding="utf-8"))
        payload["source"] = "imported"
        for model in (payload.get("models") or {}).values():
            if isinstance(model, dict):
                model["prefix"] = (model.get("prefix") or "").rstrip(" ,，")
        return payload

    models = _read("models.json")
    # 模型前缀以 ", " 结尾时与后续标签拼接会出现双重逗号
    for model in models.values():
        if isinstance(model, dict):
            model["prefix"] = (model.get("prefix") or "").rstrip(" ,，")

    return {
        "source": "bundled" if _bundled_available() else "missing",
        "models": models,
        "danbooru": _read("danbooru.json"),
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


def export_payload() -> dict:
    """导出内置库：结构与 /prompts/library 一致，另有版本号。"""
    payload = dict(library_payload())
    payload.pop("source", None)
    return {"version": LIBRARY_VERSION, "app": "local-resource-manager", **payload}


def import_payload(payload: dict) -> dict:
    """写入用户数据目录，随后从该文件加载。"""
    if not isinstance(payload, dict) or not isinstance(payload.get("categories"), list):
        raise ValueError("不是有效的内置库文件")
    path = external_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    import json as _json

    path.write_text(_json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    reset_cache()
    loaded = library_payload()
    return {
        "categories": len(loaded.get("categories") or []),
        "characters": len(loaded.get("characters") or []),
        "presets": len(loaded.get("presets") or []),
        "templates": len(loaded.get("templates") or []),
        "danbooru": len(loaded.get("danbooru") or []),
        "path": str(path),
    }
