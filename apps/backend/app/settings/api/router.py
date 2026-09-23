"""设置路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.application.errors import SettingsError
from app.settings.application.schemas import ConsumeSettingsPatch, ScrapeSettingsPatch
from app.settings.application.service import backup_database, get_view, patch_consume, patch_scrape
from app.shared.config import settings
from app.shared.db.db import get_session

router = APIRouter()
_VERSION = "0.0.0"


def _err(exc: SettingsError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("")
@router.get("/")
async def get_settings(session: AsyncSession = Depends(get_session)):
    return await get_view(session, settings.db_path, _VERSION)


@router.patch("/scrape")
async def patch_scrape_settings(
    body: ScrapeSettingsPatch,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await patch_scrape(session, body, settings.db_path, _VERSION)
    except SettingsError as exc:
        raise _err(exc) from exc


@router.patch("/consume")
async def patch_consume_settings(
    body: ConsumeSettingsPatch,
    session: AsyncSession = Depends(get_session),
):
    return await patch_consume(session, body, settings.db_path, _VERSION)


@router.post("/backup")
async def post_backup():
    try:
        return backup_database(settings.db_path)
    except SettingsError as exc:
        raise _err(exc) from exc
