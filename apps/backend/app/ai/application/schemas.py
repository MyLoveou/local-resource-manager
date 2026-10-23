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


class AIVLMRuntime(ApiModel):
    running: bool
    url: str
    binary_path: str = ""
    detected: bool = False
    models_dir: str = ""
    error: str = ""


class AIVLMModelInfo(ApiModel):
    name: str
    size_bytes: int = 0
    capabilities: list[str] = []
    supports_vision: bool = False
    selected: bool = False


class AIStatus(ApiModel):
    dependency_ready: bool
    model: AIModelInfo
    indexed: int
    total: int
    person_count_indexed: int = 0
    caption_ready: bool = False
    caption_model: str = ""
    caption_indexed: int = 0
    vlm_runtime_ready: bool = False
    vlm_models: list[str] = []
    vlm_model_details: list[AIVLMModelInfo] = []
    index_updated_at: str | None = None


class AIJob(ApiModel):
    id: str
    kind: str
    status: str
    total: int
    done: int
    failed: int = 0
    percent: int | None = None
    message: str
    created_at: str
    updated_at: str


class AIQueryInsight(ApiModel):
    source: str
    raw: str = ""
    semantic_text: str = ""
    strategy: str = ""
    caption: str = ""
    short_caption: str = ""
    tags: list[str] = []
    labels: list[str] = []
    filters: list[str] = []
    person_count: int | None = None
    orientation: str | None = None
    notes: list[str] = []


class AIMatchExplanation(ApiModel):
    resource_id: int
    reasons: list[str] = []
    semantic_score: float | None = None
    duplicate_score: float | None = None
    dhash_distance: int | None = None
    caption: str = ""
    short_caption: str = ""
    tags: list[str] = []
    matched_labels: list[str] = []
    person_count: int | None = None
    orientation: str | None = None


class AISearchResponse(ApiModel):
    items: list[Resource]
    scores: list[float]
    indexed: int
    matched: int
    returned: int
    filters: list[str] = []
    query_insight: AIQueryInsight | None = None
    explanations: list[AIMatchExplanation] = []


class AISimilarResponse(ApiModel):
    mode: str
    indexed: int
    returned: int
    items: list[Resource]
    scores: list[float]
    duplicates: list[Resource] = []
    duplicate_scores: list[float] = []
    query_insight: AIQueryInsight | None = None
    explanations: list[AIMatchExplanation] = []
    duplicate_explanations: list[AIMatchExplanation] = []


class AIFusionRequest(ApiModel):
    resource_id: int
    query: str
    limit: int = 30
    strict: bool = False
    image_weight: float = 0.5
    text_weight: float = 0.5


class AIFusionResponse(ApiModel):
    mode: str
    indexed: int
    matched: int
    returned: int
    items: list[Resource]
    scores: list[float]
    filters: list[str] = []


class AISimilarFileRequest(ApiModel):
    filename: str = ""
    data_base64: str
    mode: str = "auto"
    limit: int = 30


class AIAnalyzeRequest(ApiModel):
    resource_ids: list[int] | None = None
    only_pending: bool = True


class VLMPullRequest(ApiModel):
    model: str


class VLMSelectRequest(ApiModel):
    model: str


class VLMSelectBinaryRequest(ApiModel):
    path: str
