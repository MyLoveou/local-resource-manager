from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.download.api.router import router as download_router
from app.library.api.router import router as library_router
from app.library.infrastructure.repositories import ResourceRepository
from app.library.infrastructure.seed import replace_remote_demo_covers, seed_demo_if_empty
from app.scrape.api.router import router as scrape_router
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
            if is_new:
                inserted = await seed_demo_if_empty(repo)
                if inserted:
                    logger.info("空库已写入 %s 条演示资源", inserted)
            else:
                rewritten = await replace_remote_demo_covers(repo)
                if rewritten:
                    logger.info("已将 %s 条远程演示封面改为本地图", rewritten)
    except Exception as e:
        logger.error(f"数据库启动失败: {e}")
        raise
    yield
    logger.info("数据库关闭连接")
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
app.include_router(library_router, prefix="/library")
app.include_router(scrape_router, prefix="/scrape")
app.include_router(download_router, prefix="/download")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "backend", "version": "0.0.0"}
