from contextlib import asynccontextmanager, suppress

import asyncio
import shutil
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.ai.api.router import router as ai_router
from app.ai.application.jobs import Job, jobs
from app.ai.application.service import AIService
from app.ai.infrastructure.model_store import MODEL_ID, is_installed
from app.ai.infrastructure import ollama_runtime
from app.library.api.router import router as library_router
from app.library.infrastructure.repositories import ResourceRepository
from app.library.infrastructure.seed import replace_remote_demo_covers
from app.scrape.api.router import router as scrape_router
from app.settings.api.router import router as settings_router
from app.scrape.application.queue import recover_unfinished, start_scrape_worker, stop_scrape_worker
from app.shared.api_envelope import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
    wrap_json_envelope,
)
from app.shared.config import settings
from app.shared.db.db import dispose_engine, ensure_db, get_session_factory
from app.shared.image_support import register_optional_image_decoders
from app.shared.log import logger
from app.shared.runtime_paths import set_library_root
from app.shared.utils.watch_manager import watch_manager
from app.shared.utils.watch_bridge import watch_bridge
from app.shared.middleware.auth import require_token
from app.shared.middleware.logging import log_requests
from app.settings.application.service import load_watch_dirs
from app.settings.application.restore import apply_pending_restore
from app.settings.domain.constants import KEY_SYSTEM
from app.settings.infrastructure.settings_repo import SettingsRepository
from app.library.domain.models import ResourceType

register_optional_image_decoders()


async def _persist_ai_job(job: Job) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO ai_jobs "
                "(id, kind, status, total, done, failed, message, created_at, updated_at) "
                "VALUES (:id, :kind, :status, :total, :done, :failed, :message, "
                ":created_at, :updated_at) "
                "ON CONFLICT(id) DO UPDATE SET "
                "status = excluded.status, total = excluded.total, done = excluded.done, "
                "failed = excluded.failed, message = excluded.message, "
                "updated_at = excluded.updated_at"
            ),
            {
                "id": job.id,
                "kind": job.kind,
                "status": job.status,
                "total": job.total,
                "done": job.done,
                "failed": job.failed,
                "message": job.message,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            },
        )
        await session.commit()


def _prune_ai_failures() -> None:
    root = settings.db_path.parent / "ai-failures"
    if not root.is_dir():
        return
    cutoff = time.time() - settings.ai_failure_retention_days * 86400
    for path in root.iterdir():
        try:
            if path.is_dir() and path.stat().st_mtime < cutoff:
                shutil.rmtree(path)
        except OSError:
            pass


async def _auto_index_loop(factory) -> None:
    while True:
        await asyncio.sleep(max(10, int(settings.auto_index_interval)))
        try:
            if not settings.auto_index or not is_installed() or jobs.has_active():
                continue
            async with factory() as session:
                total = await session.scalar(
                    text(
                        "SELECT COUNT(DISTINCT resources.id) FROM resources "
                        "JOIN files ON files.resource_id = resources.id "
                        "WHERE resources.type = 'image' AND resources.status = 'active' "
                        "AND files.role = 'primary'"
                    )
                )
                indexed = await session.scalar(
                    text("SELECT COUNT(*) FROM ai_vectors WHERE model_id = :model"),
                    {"model": MODEL_ID},
                )
                if int(total or 0) > int(indexed or 0):
                    logger.info(
                        "auto index: %s images pending",
                        int(total or 0) - int(indexed or 0),
                    )
                    await AIService(session).build_index(full=False)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("auto index failed: %s", exc)


async def _auto_start_ollama(factory) -> None:
    if not settings.ollama_auto_start:
        return
    if (settings.vlm_provider or "ollama").strip().lower() != "ollama":
        return
    try:
        async with factory() as session:
            preferred = await session.scalar(
                text("SELECT value FROM ai_preferences WHERE key = 'ollama_bin'")
            )
        binary = ollama_runtime.detect_binary(str(preferred or ""))
        if not binary:
            logger.info("Ollama 自动启动跳过：未检测到 ollama.exe")
            return
        if await ollama_runtime.is_running():
            logger.info("Ollama 已在运行：%s", settings.vlm_url)
            return
        await ollama_runtime.start_runtime(binary)
        logger.info("Ollama 自动启动完成：%s", settings.vlm_url)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - AI service remains optional
        logger.warning("Ollama 自动启动失败：%s", exc)


def parse_watch_dirs(raw: dict[str, list[str]]) -> dict[ResourceType, list[str]]:
    """设置里的字符串键 → ResourceType；无效键记日志跳过。"""
    parsed: dict[ResourceType, list[str]] = {}
    for key, dirs in raw.items():
        try:
            parsed[ResourceType(key)] = dirs
        except ValueError:
            logger.warning("未知资源类型的监视目录配置，跳过: %s", key)
    return parsed



@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动：已有库则连接；无库则创建。演示封面仅在需要时处理。"""
    db_path = settings.db_path.resolve()
    ollama_task: asyncio.Task[None] | None = None
    try:
        if apply_pending_restore(db_path):
            logger.info("已应用待恢复备份")
        is_new = ensure_db()
        _prune_ai_failures()
        if is_new:
            logger.info("已创建数据库 %s", db_path)
        else:
            logger.info("已连接数据库 %s", db_path)
        if not settings.token:
            logger.warning("BACKEND_TOKEN 未配置：本次启动不校验鉴权（仅限本机开发）")
        factory = get_session_factory()
        jobs.set_persister(_persist_ai_job)
        async with factory() as session:
            stored_system = await SettingsRepository(session).get_json(KEY_SYSTEM)
            stored_library = stored_system.get("library_path")
            if isinstance(stored_library, str) and stored_library.strip():
                set_library_root(Path(stored_library.strip()))
        async with factory() as session:
            await session.execute(
                text(
                    "UPDATE ai_jobs SET status = 'error', "
                    "message = '???????????', "
                    "updated_at = datetime('now') "
                    "WHERE status IN ('queued', 'running')"
                )
            )
            await session.commit()
        async with factory() as session:
            repo = ResourceRepository(session)
            rewritten = 0
            if not is_new:
                rewritten = await replace_remote_demo_covers(repo)
            if rewritten:
                logger.info("已将 %s 条远程演示封面改为本地图", rewritten)
        start_scrape_worker()
        await recover_unfinished()
        auto_index_task = (
            asyncio.create_task(_auto_index_loop(factory))
            if settings.auto_index
            else None
        )
        ollama_task = asyncio.create_task(_auto_start_ollama(factory))

        # 监视目录：环境变量优先（锁定 UI），否则读数据库设置
        env_dirs = parse_watch_dirs(settings.watch_dirs)
        if env_dirs:
            applied_dirs = env_dirs
            logger.info("监视目录来自环境变量: %s", env_dirs)
        else:
            async with factory() as session:
                applied_dirs = parse_watch_dirs(await load_watch_dirs(session))
            logger.info("监视目录来自设置: %s", applied_dirs)

        watch_bridge.start()
        watch_manager.apply(applied_dirs, callbacks=watch_bridge.callbacks())
        # 补扫：后台未运行期间放进监视目录的文件，合成事件补导入
        if applied_dirs:
            asyncio.create_task(watch_bridge.catch_up(applied_dirs))

    except Exception as e:
        logger.error(f"数据库启动失败: {e}")
        raise
    yield
    logger.info("数据库关闭连接")
    if ollama_task is not None:
        ollama_task.cancel()
    await stop_scrape_worker()
    watch_manager.shutdown()
    await watch_bridge.stop()
    await dispose_engine()


app = FastAPI(
    title="backend",
    version="0.0.0",
    description="本地资源管理器后端：library / scrape / settings 以 APIRouter 挂入（下载不自建，D-20261007-01）",
    lifespan=lifespan,
)

app.middleware("http")(log_requests)
app.middleware("http")(require_token)
app.middleware("http")(wrap_json_envelope)

# CORS：Electron 渲染进程与后端端口不同源，需允许跨源（token 鉴权，非 cookie）。
# 必须在**最后**注册（Starlette 里最后注册的中间件在最外层），否则：
# 1) 预检 OPTIONS 会先被鉴权中间件 401，浏览器随后拒绝发出真正请求；
# 2) 401 响应不带 CORS 头，渲染进程只能看到 "Network Error"，看不到真实原因。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(library_router, prefix="/library")
app.include_router(ai_router, prefix="/ai")
app.include_router(scrape_router, prefix="/scrape")
app.include_router(settings_router, prefix="/settings")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "backend", "version": "0.0.0"}
