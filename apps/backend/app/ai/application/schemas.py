"""AI API schemas."""

from __future__ import annotations

from app.library.domain.models import Resource
from app.shared.models import ApiModel


class AIModelInfo(ApiModel):
    id: str
    name: str
    installed: bool
    dim: int
    size_bytes: int


class AIStatus(ApiModel):
    dependency_ready: bool
    model: AIModelInfo
    indexed: int
    total: int
    person_count_indexed: int = 0
    index_updated_at: str | None = None


class AIJob(ApiModel):
    id: str
    kind: str
    status: str
    total: int
    done: int
    percent: int | None = None
    message: str
    created_at: str
    updated_at: str


class AISearchResponse(ApiModel):
    items: list[Resource]
    scores: list[float]
    indexed: int
    matched: int
    returned: int
    filters: list[str] = []


class AISimilarResponse(ApiModel):
    mode: str
    indexed: int
    returned: int
    items: list[Resource]
    scores: list[float]
    duplicates: list[Resource] = []
    duplicate_scores: list[float] = []
