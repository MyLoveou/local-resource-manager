"""智能导入的 API DTO（继承 ApiModel 以输出 camelCase）。"""

from __future__ import annotations

from pydantic import Field

from app.shared.models import ApiModel, StrictApiModel


class ImportAiSettings(StrictApiModel):
    """智能导入是否启用 AI 清洗标题。"""

    ai_title: bool = False


class SuggestionGroup(ApiModel):
    """一批同值建议。"""

    field: str
    value: dict | None = None
    source: str
    confidence: float
    count: int
    reasons: list[str] = Field(default_factory=list)
    suggestion_ids: list[int] = Field(default_factory=list)
    sample_resource_ids: list[int] = Field(default_factory=list)


class SuggestionPage(ApiModel):
    groups: list[SuggestionGroup] = Field(default_factory=list)
    total: int = 0


class SuggestionGroupKey(ApiModel):
    field: str
    value: dict | None = None


class SuggestionApplyRequest(StrictApiModel):
    ids: list[int] | None = None
    groups: list[SuggestionGroupKey] | None = None
    min_confidence: float | None = None


class SuggestionRejectRequest(StrictApiModel):
    ids: list[int] | None = None
    groups: list[SuggestionGroupKey] | None = None
    all: bool | None = None


class SuggestionSummary(ApiModel):
    pending: int = 0
    high_confidence: int = 0
    jobs: int = 0


class SuggestionApplyResult(ApiModel):
    accepted: int = 0
    skipped: int = 0
    updated_resources: int = 0


class SuggestionRejectResult(ApiModel):
    rejected: int = 0
