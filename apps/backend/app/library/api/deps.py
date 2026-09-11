"""Library API 依赖。"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.db import get_session


def get_repos(
    session: AsyncSession = Depends(get_session),
) -> tuple[ResourceRepository, TaskSummaryRepository]:
    """每请求一个 AsyncSession 上的仓储。"""
    return ResourceRepository(session), TaskSummaryRepository(session)
