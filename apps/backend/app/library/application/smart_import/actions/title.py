"""clean-title 动作：把发布组命名收成更像标题的字符串。

目录名优先（D-20261025-02 · Q5）：目录名清洗后置信度 >= 0.5 才压过文件名。
"""

from __future__ import annotations

from app.library.application.smart_import.base import (
    ActionContext,
    Suggestion,
    register,
)
from app.library.application.smart_import.suspect import (
    describe_suspicion,
    suspicion_reasons,
)
from app.library.application.smart_import.title_clean import (
    clean_release_name,
    describe_removed,
)
from app.library.domain.models import ResourceType

_DIR_MIN_CONFIDENCE = 0.5

# 有可疑残留时压低置信度，避免默认勾选把脏标题写进库
_SUSPECT_CONFIDENCE_CAP = 0.55

# 系列作品的集号在季/集树里；单文件视频每个文件就是一条资源，编号是身份
_SERIES_TYPES = frozenset({ResourceType.ANIME, ResourceType.AV})


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
        keep_episode = ctx.type not in _SERIES_TYPES
        chosen = None
        origin = ctx.file_stem
        if ctx.dir_name:
            by_dir = clean_release_name(ctx.dir_name, keep_episode=keep_episode)
            if by_dir.title and by_dir.confidence >= _DIR_MIN_CONFIDENCE:
                chosen = by_dir
                origin = ctx.dir_name
        if chosen is None:
            by_file = clean_release_name(ctx.file_stem, keep_episode=keep_episode)
            if by_file.confidence > 0:
                chosen = by_file
                origin = ctx.file_stem

        if chosen is None or chosen.confidence <= 0:
            return []
        if not chosen.title or chosen.title == ctx.file_stem:
            return []

        reason = describe_removed(chosen.removed) or "规范化标题"
        confidence = chosen.confidence
        leftover = suspicion_reasons(origin, chosen.title)
        if leftover:
            confidence = min(confidence, _SUSPECT_CONFIDENCE_CAP)
            reason = f"{reason}；{describe_suspicion(leftover)}"

        return [
            Suggestion(
                field=self.field,
                value={"text": chosen.title},
                confidence=confidence,
                reason=reason,
                source="rule",
            )
        ]


register(CleanTitleAction())
