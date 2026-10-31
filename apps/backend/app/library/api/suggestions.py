"""导入建议（smart-import S1）。

- `GET  /library/import-suggestions`         按 (field, value) 分组拉取
- `GET  /library/import-suggestions/summary` 待审阅计数（顶栏角标）
- `POST /library/import-suggestions/apply`   采纳
- `POST /library/import-suggestions/reject`  忽略
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.smart_import.pipeline import suggestion_page
from app.library.application.smart_import.preferences import is_ai_enabled, set_ai_enabled
from app.library.application.smart_import.schemas import (
    ImportAiSettings,
    SuggestionApplyRequest,
    SuggestionApplyResult,
    SuggestionPage,
    SuggestionRejectRequest,
    SuggestionRejectResult,
    SuggestionSummary,
)
from app.library.infrastructure.repositories_suggestions import SuggestionRepository
from app.shared.db.db import get_session

router = APIRouter(prefix="/import-suggestions", tags=["library-suggestions"])


@router.get("", response_model=SuggestionPage)
async def list_suggestions(
    job_id: str | None = Query(default=None, alias="jobId"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> SuggestionPage:
    page = await suggestion_page(
        SuggestionRepository(session), job_id=job_id, limit=limit, offset=offset
    )
    return SuggestionPage(**page)


@router.get("/summary", response_model=SuggestionSummary)
async def suggestions_summary(
    session: AsyncSession = Depends(get_session),
) -> SuggestionSummary:
    return SuggestionSummary(**await SuggestionRepository(session).summary())


@router.get("/settings", response_model=ImportAiSettings)
async def get_import_settings(
    session: AsyncSession = Depends(get_session),
) -> ImportAiSettings:
    return ImportAiSettings(ai_title=await is_ai_enabled(session))


@router.put("/settings", response_model=ImportAiSettings)
async def update_import_settings(
    body: ImportAiSettings,
    session: AsyncSession = Depends(get_session),
) -> ImportAiSettings:
    await set_ai_enabled(session, body.ai_title)
    return ImportAiSettings(ai_title=body.ai_title)


@router.post("/apply", response_model=SuggestionApplyResult)
async def apply_suggestions(
    body: SuggestionApplyRequest,
    session: AsyncSession = Depends(get_session),
) -> SuggestionApplyResult:
    groups = [(group.field, group.value) for group in body.groups or []] or None
    result = await SuggestionRepository(session).apply(
        ids=body.ids, groups=groups, min_confidence=body.min_confidence
    )
    return SuggestionApplyResult(**result)


@router.post("/reject", response_model=SuggestionRejectResult)
async def reject_suggestions(
    body: SuggestionRejectRequest,
    session: AsyncSession = Depends(get_session),
) -> SuggestionRejectResult:
    groups = [(group.field, group.value) for group in body.groups or []] or None
    result = await SuggestionRepository(session).reject(
        ids=body.ids, groups=groups, reject_all=bool(body.all)
    )
    return SuggestionRejectResult(**result)
