from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.download.api.routes import app as download_app
from app.library.api.routes import app as library_app
from app.scrape.api.routes import app as scrape_app
from app.shared.config import settings
from app.shared.db.db import init_db
from app.shared.log import logger
from app.shared.middleware.logging import log_requests


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动时初始化数据库并执行迁移。"""
    logger.info("启动时初始化数据库并执行迁移")
    try: 
        logger.info("正在初始化数据库")
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        raise
    yield
    logger.info("数据库关闭连接")


app = FastAPI(
    title="backend",
    version="0.0.0",
    description="本地资源管理器后端服务：内挂资源库/抓取/下载三个子应用",
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

app.mount("/library", library_app)
app.mount("/scrape", scrape_app)
app.mount("/download", download_app)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "backend", "version": "0.0.0"}
