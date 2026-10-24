"""Small, curated visual label vocabulary for Chinese-CLIP zero-shot tagging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelSpec:
    label: str
    group: str
    prompt: str
    max_per_group: int = 1


def _specs() -> list[LabelSpec]:
    scene = (
        "室内",
        "室外",
        "海边",
        "街道",
        "舞台",
        "摄影棚",
        "卧室",
        "餐厅",
        "森林",
        "夜景",
        "雨天",
        "雪景",
        "建筑",
        "花园",
    )
    action = (
        "跑步",
        "站立",
        "坐着",
        "躺着",
        "自拍",
        "合影",
        "跳舞",
        "拥抱",
        "看镜头",
        "吃东西",
    )
    color = (
        "红色",
        "黑色",
        "白色",
        "蓝色",
        "绿色",
        "黄色",
        "粉色",
        "紫色",
        "银色",
        "金色",
    )
    objects = (
        "帽子",
        "眼镜",
        "口罩",
        "手机",
        "相机",
        "花",
        "树",
        "水",
        "汽车",
        "猫",
        "狗",
        "书",
    )
    style = ("cosplay", "古风", "赛博朋克", "胶片", "黑白", "二次元")
    clothing = ("裙子", "制服", "和服", "西装", "外套", "泳装")

    specs: list[LabelSpec] = []
    for label in scene:
        specs.append(LabelSpec(label, "scene", f"一张在{label}拍摄的照片"))
    for label in action:
        specs.append(LabelSpec(label, "action", f"一张{label}的照片"))
    for label in color:
        specs.append(LabelSpec(label, "color", f"一张以{label}为主的照片", 2))
    for label in objects:
        specs.append(LabelSpec(label, "object", f"一张包含{label}的照片", 2))
    for color in ("红色", "黑色", "白色", "蓝色", "粉色", "紫色", "绿色", "黄色", "银色"):
        specs.append(LabelSpec(f"{color}帽子", "object", f"一张戴{color}帽子的照片", 2))
    for label in style:
        specs.append(LabelSpec(label, "style", f"一张{label}风格的照片"))
    for label in clothing:
        specs.append(LabelSpec(label, "clothing", f"一张穿{label}的照片", 2))
    return specs


LABELS = _specs()
PROMPTS = tuple(spec.prompt for spec in LABELS)
THRESHOLDS = {
    "scene": 0.34,
    "action": 0.335,
    "color": 0.34,
    "object": 0.34,
    "style": 0.35,
    "clothing": 0.34,
}

# Long aliases must be checked before their shorter components.
ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("红色帽子", ("红色帽子",)),
    ("红帽子", ("红色帽子",)),
    ("黑色帽子", ("黑色帽子",)),
    ("黑帽子", ("黑色帽子",)),
    ("蓝色帽子", ("蓝色帽子",)),
    ("蓝帽子", ("蓝色帽子",)),
    ("白色帽子", ("白色帽子",)),
    ("白帽子", ("白色帽子",)),
    ("粉色帽子", ("粉色帽子",)),
    ("粉帽子", ("粉色帽子",)),
    ("紫色帽子", ("紫色帽子",)),
    ("紫帽子", ("紫色帽子",)),
    ("绿色帽子", ("绿色帽子",)),
    ("绿帽子", ("绿色帽子",)),
    ("黄色帽子", ("黄色帽子",)),
    ("黄帽子", ("黄色帽子",)),
    ("银色帽子", ("银色帽子",)),
    ("银帽子", ("银色帽子",)),
    ("跑步", ("跑步",)),
    ("海边", ("海边",)),
    ("室外", ("室外",)),
    ("室内", ("室内",)),
    ("夜景", ("夜景",)),
    ("自拍", ("自拍",)),
    ("合影", ("合影",)),
    ("帽子", ("帽子",)),
    ("眼镜", ("眼镜",)),
    ("口罩", ("口罩",)),
    ("手机", ("手机",)),
    ("相机", ("相机",)),
    ("红色", ("红色",)),
    ("黑色", ("黑色",)),
    ("白色", ("白色",)),
    ("蓝色", ("蓝色",)),
    ("绿色", ("绿色",)),
    ("黄色", ("黄色",)),
    ("粉色", ("粉色",)),
    ("紫色", ("紫色",)),
    ("银色", ("银色",)),
    ("金色", ("金色",)),
    ("裙子", ("裙子",)),
    ("制服", ("制服",)),
    ("和服", ("和服",)),
    ("西装", ("西装",)),
    ("外套", ("外套",)),
    ("cosplay", ("cosplay",)),
    ("古风", ("古风",)),
    ("赛博朋克", ("赛博朋克",)),
)


def labels_in_query(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    consumed: list[str] = []
    for alias, labels in ALIASES:
        if alias not in lowered:
            continue
        if any(alias in other for other in consumed):
            continue
        consumed.append(alias)
        for label in labels:
            if label not in found:
                found.append(label)
    return found


def select_labels(scores: list[float]) -> list[tuple[LabelSpec, float]]:
    """Pick the strongest labels per group above a group-specific threshold."""
    selected: list[tuple[LabelSpec, float]] = []
    for spec, score in zip(LABELS, scores, strict=True):
        threshold = THRESHOLDS.get(spec.group, 0.34)
        if score >= threshold:
            selected.append((spec, float(score)))
    result: list[tuple[LabelSpec, float]] = []
    for group in {spec.group for spec in LABELS}:
        group_items = sorted(
            (item for item in selected if item[0].group == group),
            key=lambda item: item[1],
            reverse=True,
        )
        limit = max((spec.max_per_group for spec in LABELS if spec.group == group), default=1)
        result.extend(group_items[:limit])
    return sorted(result, key=lambda item: item[1], reverse=True)
