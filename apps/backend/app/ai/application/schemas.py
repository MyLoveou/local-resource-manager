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
    vlm_provider: str = "ollama"
    anime_tagger_ready: bool = False
    anime_tagger_size: int = 0
    vlm_models: list[str] = []
    vlm_model_details: list[AIVLMModelInfo] = []
    index_updated_at: str | None = None


class AIDeviceInfo(ApiModel):
    cpu_count: int
    memory_total_bytes: int
    memory_available_bytes: int = 0
    gpu_name: str = ""
    vram_total_bytes: int = 0
    vram_free_bytes: int = 0
    platform: str = ""


class AIPerformance(ApiModel):
    device: AIDeviceInfo
    mode: str = "balanced"
    manual: int = 1
    effective: int = 1
    safe: int = 1
    balanced: int = 1
    max: int = 1


class AIPerformancePatch(ApiModel):
    mode: str | None = None
    manual: int | None = None


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
    min_score: float = 0.0
    filtered_low_score: int = 0
    caption_matched: int = 0
    feedback_adjusted: int = 0
    feedback: dict[int, str] = {}
    explored: bool = False


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


class AIEntitySuggestion(ApiModel):
    id: int
    name: str


class AISuggestionItem(ApiModel):
    resource_id: int
    title: str
    thumbnail_path: str | None = None
    tags: list[str] = []
    characters: list[AIEntitySuggestion] = []
    persons: list[AIEntitySuggestion] = []
    collections: list[AIEntitySuggestion] = []


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


class AIIndexRequest(ApiModel):
    full: bool = False


class AIFeedbackRequest(ApiModel):
    query: str
    resource_id: int
    action: str
    source: str = "search"
    score: float | None = None
    position: int | None = None
    features: dict | None = None


class VLMPullRequest(ApiModel):
    model: str


class VLMSelectRequest(ApiModel):
    model: str


class VLMSelectBinaryRequest(ApiModel):
    path: str
