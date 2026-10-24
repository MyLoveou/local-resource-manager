"""设置路由。"""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.application.errors import SettingsError
from app.settings.application.schemas import ConsumeSettingsPatch, ParseRulesPatch, RestorePrepareRequest, RestorePrepareResult, ScrapeSettingsPatch, SystemSettingPatch, WatchSettingsPatch
from app.settings.application.service import backup_database, backup_library, get_view, patch_consume, patch_parse, patch_scrape, patch_watch, pathc_system_settings
from app.settings.application.restore import prepare_restore
from app.shared.config import settings
from app.shared.db.db import get_session
from app.shared.log import logger
router = APIRouter()
_VERSION = os.environ.get("BACKEND_VERSION", "0.0.0")


def _err(exc: SettingsError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("")
@router.get("/")
async def get_settings(session: AsyncSession = Depends(get_session)):
    return await get_view(session, settings.db_path, _VERSION)

# 更新刮削设置
@router.patch("/scrape")
async def patch_scrape_settings(
    body: ScrapeSettingsPatch,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await patch_scrape(session, body, settings.db_path, _VERSION)
    except SettingsError as exc:
        raise _err(exc) from exc

# 更新消费渠道设置
@router.patch("/consume")
async def patch_consume_settings(
    body: ConsumeSettingsPatch,
    session: AsyncSession = Depends(get_session),
):
    return await patch_consume(session, body, settings.db_path, _VERSION)

# 备份库
@router.post("/backup")
async def post_backup():
    try:
        return backup_database(settings.db_path)
    except SettingsError as exc:
        raise _err(exc) from exc


@router.post("/backup/full")
async def post_backup_full(session: AsyncSession = Depends(get_session)):
    try:
        view = await get_view(session, settings.db_path, _VERSION)
        return backup_library(settings.db_path, Path(view.system.backup_dir))
    except SettingsError as exc:
        raise _err(exc) from exc


@router.post("/restore/prepare", response_model=RestorePrepareResult)
async def post_restore_prepare(body: RestorePrepareRequest):
    try:
        pending = prepare_restore(settings.db_path, Path(body.path))
        return RestorePrepareResult(path=str(pending), restart_required=True)
    except SettingsError as exc:
        raise _err(exc) from exc

# 更新设置
@router.patch("/system")
async def pathc_settings(body: SystemSettingPatch, session: AsyncSession = Depends(get_session)):
    logger.info('patch_settings: %s', body)
    return await pathc_system_settings(session, body, settings.db_path, _VERSION)

# 更新监视目录
@router.patch("/watch")
async def patch_watch_settings(
    body: WatchSettingsPatch,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await patch_watch(session, body, settings.db_path, _VERSION)
    except SettingsError as exc:
        raise _err(exc) from exc

# 更新视频文件名解析规则
@router.patch("/parse")
async def patch_parse_settings(
    body: ParseRulesPatch,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await patch_parse(session, body, settings.db_path, _VERSION)
    except SettingsError as exc:
        raise _err(exc) from exc
