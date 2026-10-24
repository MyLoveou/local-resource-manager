"""设置：刮削凭证掩码、路径、备份。"""

from __future__ import annotations

import asyncio
import re
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.packages.resource_package import default_library_store
from app.settings.application.errors import SettingsError
from app.settings.application.watch_dirs import normalize_watch_dirs, validate_watch_dirs
from app.library.application.workbench import load_channels, save_channels, save_system_settings
from app.library.application.video_naming import invalidate_user_rules
from app.library.domain.models import ResourceType
from app.settings.application.schemas import (
    BackupResult,
    ConsumeSettingsOut,
    ConsumeSettingsPatch,
    MikanState,
    ParseRulesOut,
    ParseRulesPatch,
    ScrapeSettingsOut,
    ScrapeSettingsPatch,
    SecretState,
    SettingsView,
    SystemSettingsOut,
    SystemSettingPatch,
    WatchSettingsOut,
    WatchSettingsPatch,
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
from app.settings.domain.constants import KEY_BANGUMI, KEY_MIKAN, KEY_PARSE, KEY_TMDB, KEY_WATCH, KEY_SYSTEM
from app.settings.infrastructure.settings_repo import SettingsRepository
from app.shared.log import logger
from app.shared.runtime_paths import set_library_root
from app.shared.utils.watch_manager import watch_manager
from app.shared.utils.watch_bridge import watch_bridge


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


def _default_download_dir(db_path: Path) -> Path:
    """下载目录默认值：第三方下载器的输出目录（入库靠监视该目录，D-20261007-01）。"""
    return db_path.parent / "downloads"


def system_from_store(stored: dict, process_db: Path, backend_version: str) -> SystemSettingsOut:
    """已保存路径优先；未写过的键按当前库文件位置回落。"""
    anchor = (_stored_path(stored, "db_path") or process_db).resolve()
    library = _stored_path(stored, "library_path") or default_library_store(anchor)
    log_dir = _stored_path(stored, "log_dir") or resolve_log_dir()
    downloads = _stored_path(stored, "download_dir") or _default_download_dir(anchor)
    backups = _stored_path(stored, "backup_dir") or backup_dir(anchor)
    return SystemSettingsOut(
        db_path=str(anchor),
        library_path=str(library.resolve()),
        log_dir=str(log_dir.resolve()),
        download_dir=str(downloads.resolve()),
        backup_dir=str(backups.resolve()),
        backend_version=backend_version,
    )


async def load_watch_dirs(session: AsyncSession) -> dict[str, list[str]]:
    """已保存的监视目录（归一化后）。"""
    raw = await SettingsRepository(session).get_json(KEY_WATCH)
    dirs = raw.get("dirs")
    return normalize_watch_dirs(dirs if isinstance(dirs, dict) else {})


def env_watch_dirs() -> bool:
    """监视目录是否由环境变量锁定。"""
    import os

    return bool(os.environ.get("BACKEND_WATCH_DIRS"))


async def load_parse_rules_raw(session: AsyncSession) -> list[str]:
    raw = await SettingsRepository(session).get_json(KEY_PARSE)
    rules = raw.get("rules")
    return [str(item) for item in rules] if isinstance(rules, list) else []


async def load_parse_flags(session: AsyncSession) -> tuple[bool, bool]:
    raw = await SettingsRepository(session).get_json(KEY_PARSE)
    return bool(raw.get("titleWithEp")), bool(raw.get("autoCollection"))


async def get_view(session: AsyncSession, db_path: Path, backend_version: str) -> SettingsView:
    invalidate_secret_cache()
    tmdb, bangumi, mikan = await asyncio.to_thread(
        lambda: (tmdb_api_key(), bangumi_token(), mikan_base_url())
    )
    stored = await SettingsRepository(session).get_json(KEY_SYSTEM)
    channels = await load_channels(session)
    watch_dirs = await load_watch_dirs(session)
    title_with_ep, auto_collection = await load_parse_flags(session)
    return SettingsView(
        scrape=ScrapeSettingsOut(
            tmdb=_secret_state(tmdb, bool(env_tmdb_key())),
            bangumi=_secret_state(bangumi, bool(env_bangumi_token())),
            mikan=MikanState(base_url=mikan, env_locked=bool(env_mikan_base())),
        ),
        system=system_from_store(stored, db_path, backend_version),
        consume=ConsumeSettingsOut(channels=channels),
        watch=WatchSettingsOut(dirs=watch_dirs, env_locked=env_watch_dirs()),
        parse=ParseRulesOut(
            rules=await load_parse_rules_raw(session),
            title_with_ep=title_with_ep,
            auto_collection=auto_collection,
        ),
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


async def patch_watch(
    session: AsyncSession,
    body: WatchSettingsPatch,
    db_path: Path,
    backend_version: str,
) -> SettingsView:
    """保存监视目录：归一化 + 校验 + 持久化 + 重配监视器。"""
    if env_watch_dirs():
        raise SettingsError("监视目录由环境变量提供，不能在此修改", 400)
    normalized = normalize_watch_dirs(body.dirs)
    validate_watch_dirs(normalized)
    await SettingsRepository(session).put_json(KEY_WATCH, {"dirs": normalized})
    applied = {ResourceType(key): dirs for key, dirs in normalized.items()}
    await asyncio.to_thread(watch_manager.apply, applied)
    # 重配后补扫新目录，把后台未运行期间放入的文件补导入
    if applied:
        asyncio.create_task(watch_bridge.catch_up(applied))
    return await get_view(session, db_path, backend_version)


async def patch_parse(
    session: AsyncSession,
    body: ParseRulesPatch,
    db_path: Path,
    backend_version: str,
) -> SettingsView:
    """保存视频文件名解析规则与开关：正则逐条校验，无效 400；保存后失效缓存。"""
    current = await SettingsRepository(session).get_json(KEY_PARSE)
    merged = {
        "rules": list(current.get("rules") or []),
        "titleWithEp": bool(current.get("titleWithEp")),
        "autoCollection": bool(current.get("autoCollection")),
    }
    if body.rules is not None:
        rules = [str(item).strip() for item in body.rules if isinstance(item, str) and item.strip()]
        for rule in rules:
            try:
                re.compile(rule)
            except re.error as exc:
                raise SettingsError(f"无效正则：{exc}", 400) from exc
        merged["rules"] = rules
    if body.title_with_ep is not None:
        merged["titleWithEp"] = body.title_with_ep
    if body.auto_collection is not None:
        merged["autoCollection"] = body.auto_collection
    await SettingsRepository(session).put_json(KEY_PARSE, merged)
    invalidate_user_rules()
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
        raw_value = str(value).strip()
        if raw_value:
            merged[key] = raw_value
    requested_library = merged.get("library_path")
    current_library = stored.get("library_path")
    requested_db = merged.get("db_path")
    if requested_db and Path(requested_db).resolve() != db_path.resolve():
        raise SettingsError(
            "数据库路径不能在线修改；请通过 BACKEND_DB_PATH 或重启迁移", 400
        )
    if requested_library and requested_library != current_library:
        resource_count = int(
            await session.scalar(text("SELECT COUNT(*) FROM resources")) or 0
        )
        if resource_count:
            raise SettingsError(
                "已有资源时不能直接切换资源库路径；请先导出/迁移资源库", 400
            )
        set_library_root(Path(requested_library))
        logger.info("library path switched: %s", requested_library)
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


def backup_library(db_path: Path, dest_dir: Path | None = None) -> BackupResult:
    """Back up SQLite plus the managed library directory into one ZIP."""
    source = db_path.resolve()
    if not source.is_file():
        raise SettingsError("数据库文件不存在", 400)
    target_dir = (dest_dir or backup_dir(source)).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = target_dir / f"library-{stamp}.zip"
    temp_db = target_dir / f".library-{stamp}.db"
    src = sqlite3.connect(str(source))
    dst = sqlite3.connect(str(temp_db))
    try:
        src.backup(dst)
    except sqlite3.Error as exc:
        dst.close()
        src.close()
        temp_db.unlink(missing_ok=True)
        raise SettingsError(f"数据库快照失败:{exc}", 500) from exc
    dst.close()
    src.close()

    library = default_library_store(source)
    try:
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(temp_db, "library.db")
            if library.is_dir():
                for path in sorted(library.rglob("*")):
                    if path.is_file():
                        archive.write(path, f"library/{path.relative_to(library).as_posix()}")
    except OSError as exc:
        dest.unlink(missing_ok=True)
        raise SettingsError(f"备份资源库失败:{exc}", 500) from exc
    finally:
        temp_db.unlink(missing_ok=True)
    return BackupResult(path=str(dest))
