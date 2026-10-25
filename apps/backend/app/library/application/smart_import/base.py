"""智能导入：动作模型与注册表（S1）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.library.domain.models import ResourceType


@dataclass(frozen=True)
class ActionContext:
    """一次导入动作的输入。全部来自导入期可得的信息，不查模型。"""

    resource_id: int
    type: ResourceType
    file_stem: str
    dir_name: str | None = None
    existing_categories: tuple[str, ...] = ()
    prefer_episode_in_title: bool = False


@dataclass(frozen=True)
class Suggestion:
    """一条建议。没有理由的建议不展示（L1 §8）。"""

    field: str
    value: dict | None
    confidence: float
    reason: str
    source: str = "rule"


class ImportAction(Protocol):
    field: str
    applies_to: frozenset[ResourceType]

    def evaluate(self, ctx: ActionContext) -> list[Suggestion]: ...


_REGISTRY: dict[ResourceType, list[ImportAction]] = {}


def register(action: ImportAction) -> ImportAction:
    """按类型登记动作；同一类型可有多个动作。"""
    for type_ in action.applies_to:
        _REGISTRY.setdefault(type_, []).append(action)
    return action


def actions_for(type_: ResourceType) -> list[ImportAction]:
    return list(_REGISTRY.get(type_, ()))


def clear_registry() -> None:
    """测试用。"""
    _REGISTRY.clear()
