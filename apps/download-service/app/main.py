from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="download-service",
    version="0.0.0",
    description="下载服务：编排层 + aria2c/rqbit 双引擎 + yt-dlp 站点兜底",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "download", "version": "0.0.0"}
