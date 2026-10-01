"""设置：刮削凭证掩码、路径、备份。"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.download.application.service import staging_root
from app.library.application.packages.resource_package import default_library_store
from app.settings.application.errors import SettingsError
from app.library.application.workbench import load_channels, save_channels, save_system_settings
from app.settings.application.schemas import (
    BackupResult,
    ConsumeSettingsOut,
    ConsumeSettingsPatch,
    MikanState,
    ScrapeSettingsOut,
    ScrapeSettingsPatch,
    SecretState,
    SettingsView,
    SystemSettingsOut,
    SystemSettingPatch,
)
from app.settings.application.secrets import (
    bangumi_token,
    env_bangumi_token,
    env_mikan_base,
    env_tmdb_key,
    invalidate_secret_cache,
    mikan_base_url,
    remember,
    tmdb_api_key,
)
from app.shared.config import resolve_log_dir
from app.settings.domain.constants import KEY_BANGUMI, KEY_MIKAN, KEY_TMDB, KEY_SYSTEM
from app.settings.infrastructure.settings_repo import SettingsRepository
from app.shared.log import logger


def _hint(secret: str) -> str | None:
    text = secret.strip()
    if not text:
        return None
    if len(text) <= 4:
        return "••••"
    return f"••••{text[-4:]}"


def _secret_state(current: str, env_locked: bool) -> SecretState:
    return SecretState(configured=bool(current), hint=_hint(current), env_locked=env_locked)


def _stored_path(stored: dict, key: str) -> Path | None:
    raw = stored.get(key)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    return Path(text) if text else None


def system_from_store(stored: dict, process_db: Path, backend_version: str) -> SystemSettingsOut:
    """已保存路径优先；未写过的键按当前库文件位置回落。"""
    anchor = (_stored_path(stored, "db_path") or process_db).resolve()
    library = _stored_path(stored, "library_path") or default_library_store(anchor)
    log_dir = _stored_path(stored, "log_dir") or resolve_log_dir()
    downloads = _stored_path(stored, "download_dir") or staging_root(anchor)
    backups = _stored_path(stored, "backup_dir") or backup_dir(anchor)
    return SystemSettingsOut(
        db_path=str(anchor),
        library_path=str(library.resolve()),
        log_dir=str(log_dir.resolve()),
        download_dir=str(downloads.resolve()),
        backup_dir=str(backups.resolve()),
        backend_version=backend_version,
    )


async def get_view(session: AsyncSession, db_path: Path, backend_version: str) -> SettingsView:
    invalidate_secret_cache()
    tmdb = tmdb_api_key()
    bangumi = bangumi_token()
    mikan = mikan_base_url()
    stored = await SettingsRepository(session).get_json(KEY_SYSTEM)
    channels = await load_channels(session)
    return SettingsView(
        scrape=ScrapeSettingsOut(
            tmdb=_secret_state(tmdb, bool(env_tmdb_key())),
            bangumi=_secret_state(bangumi, bool(env_bangumi_token())),
            mikan=MikanState(base_url=mikan, env_locked=bool(env_mikan_base())),
        ),
        system=system_from_store(stored, db_path, backend_version),
        consume=ConsumeSettingsOut(channels=channels),
    )


async def patch_scrape(
    session: AsyncSession,
    body: ScrapeSettingsPatch,
    db_path: Path,
    backend_version: str,
) -> SettingsView:
    repo = SettingsRepository(session)
    incoming = body.model_dump(exclude_unset=True)
    if "tmdb_api_key" in incoming:
        if env_tmdb_key():
            raise SettingsError("TMDB Key 由环境变量提供，不能在此修改", 400)
        key = (incoming["tmdb_api_key"] or "").strip()
        blob = {"apiKey": key} if key else {}
        await repo.put_json(KEY_TMDB, blob)
        remember(KEY_TMDB, blob)
    if "bangumi_access_token" in incoming:
        if env_bangumi_token():
            raise SettingsError("Bangumi Token 由环境变量提供，不能在此修改", 400)
        token = (incoming["bangumi_access_token"] or "").strip()
        blob = {"accessToken": token} if token else {}
        await repo.put_json(KEY_BANGUMI, blob)
        remember(KEY_BANGUMI, blob)
    if "mikan_base_url" in incoming:
        if env_mikan_base():
            raise SettingsError("蜜柑地址由环境变量提供，不能在此修改", 400)
        url = (incoming["mikan_base_url"] or "").strip().rstrip("/")
        if url:
            _assert_http_url(url)
            blob = {"baseUrl": url}
        else:
            blob = {}
        await repo.put_json(KEY_MIKAN, blob)
        remember(KEY_MIKAN, blob)
    return await get_view(session, db_path, backend_version)

# 更新消费渠道
async def patch_consume(
    session: AsyncSession,
    body: ConsumeSettingsPatch,
    db_path: Path,
    backend_version: str,
) -> SettingsView:
    payload = {key: value.model_dump() for key, value in body.channels.items()}
    await save_channels(session, payload)
    return await get_view(session, db_path, backend_version)

_SYSTEM_PATH_KEYS = ("db_path", "library_path", "log_dir", "download_dir", "backup_dir")


# 更新系统设置：只覆盖本次提交的路径，其余键保留。
async def pathc_system_settings(
    session: AsyncSession, body: SystemSettingPatch, db_path: Path, backend_version: str
) -> SettingsView:
    incoming = body.model_dump(exclude_unset=True)
    stored = await SettingsRepository(session).get_json(KEY_SYSTEM)
    merged = {key: stored[key] for key in _SYSTEM_PATH_KEYS if isinstance(stored.get(key), str)}
    for key in _SYSTEM_PATH_KEYS:
        if key not in incoming:
            continue
        value = incoming[key]
        if value is None:
            continue
        text = str(value).strip()
        if text:
            merged[key] = text
    logger.info("pathc_system_settings payload %s", merged)
    await save_system_settings(session, merged)
    return await get_view(session, db_path, backend_version)

def _assert_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise SettingsError("蜜柑地址须为 HTTP(S) URL", 400)


def backup_dir(db_path: Path) -> Path:
    return db_path.parent / "backups"


def backup_database(db_path: Path) -> BackupResult:
    source = db_path.resolve()
    if not source.is_file():
        raise SettingsError("数据库不存在", 400)
    dest_dir = backup_dir(source)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"library-{stamp}.db"
    src = sqlite3.connect(str(source))
    dst = sqlite3.connect(str(dest))
    try:
        src.backup(dst)
    except sqlite3.Error as exc:
        dst.close()
        src.close()
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise SettingsError(f"备份失败：{exc}", 500) from exc
    dst.close()
    src.close()
    return BackupResult(path=str(dest))
