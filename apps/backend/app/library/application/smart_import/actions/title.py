"""clean-title 动作：把发布组命名收成更像标题的字符串。

目录名优先（D-20261025-02 · Q5）：目录名清洗后置信度 >= 0.5 才压过文件名。
"""

from __future__ import annotations

from app.library.application.smart_import.base import (
    ActionContext,
    Suggestion,
    register,
)
from app.library.application.smart_import.title_clean import (
    clean_release_name,
    describe_removed,
)
from app.library.domain.models import ResourceType

_DIR_MIN_CONFIDENCE = 0.5


class CleanTitleAction:
    field = "title"
    applies_to = frozenset(
        {
            ResourceType.VIDEO,
            ResourceType.ANIME,
            ResourceType.AV,
            ResourceType.IMAGE,
        }
    )

    def evaluate(self, ctx: ActionContext) -> list[Suggestion]:
        chosen = None
        if ctx.dir_name:
            by_dir = clean_release_name(ctx.dir_name)
            if by_dir.title and by_dir.confidence >= _DIR_MIN_CONFIDENCE:
                chosen = by_dir
        if chosen is None:
            by_file = clean_release_name(
                ctx.file_stem, prefer_ep=ctx.prefer_episode_in_title
            )
            if by_file.confidence > 0:
                chosen = by_file

        if chosen is None or chosen.confidence <= 0:
            return []
        if not chosen.title or chosen.title == ctx.file_stem:
            return []

        reason = describe_removed(chosen.removed) or "规范化标题"
        return [
            Suggestion(
                field=self.field,
                value={"text": chosen.title},
                confidence=chosen.confidence,
                reason=reason,
                source="rule",
            )
        ]


register(CleanTitleAction())
