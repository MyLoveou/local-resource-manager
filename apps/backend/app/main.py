from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.download.api.router import router as download_router
from app.download.application.queue import recover_downloads, start_download_worker, stop_download_worker
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
from app.shared.log import logger
from app.shared.middleware.logging import log_requests


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动：已有库则连接；无库则创建。演示封面仅在需要时处理。"""
    db_path = settings.db_path.resolve()
    try:
        is_new = ensure_db()
        if is_new:
            logger.info("已创建数据库 %s", db_path)
        else:
            logger.info("已连接数据库 %s", db_path)
        factory = get_session_factory()
        async with factory() as session:
            repo = ResourceRepository(session)
            rewritten = 0
            if not is_new:
                rewritten = await replace_remote_demo_covers(repo)
            if rewritten:
                logger.info("已将 %s 条远程演示封面改为本地图", rewritten)
        start_scrape_worker()
        await recover_unfinished()
        start_download_worker()
        await recover_downloads()
    except Exception as e:
        logger.error(f"数据库启动失败: {e}")
        raise
    yield
    logger.info("数据库关闭连接")
    await stop_scrape_worker()
    await stop_download_worker()
    await dispose_engine()


app = FastAPI(
    title="backend",
    version="0.0.0",
    description="本地资源管理器后端：library / scrape / download 以 APIRouter 挂入",
    lifespan=lifespan,
)

# CORS：Electron 渲染进程与后端端口不同源，需允许跨源（token 鉴权，非 cookie）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(log_requests)
app.middleware("http")(wrap_json_envelope)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(library_router, prefix="/library")
app.include_router(scrape_router, prefix="/scrape")
app.include_router(download_router, prefix="/download")
app.include_router(settings_router, prefix="/settings")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "backend", "version": "0.0.0"}
