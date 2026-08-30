from fastapi import FastAPI

from app.download.api.routes import app as download_app
from app.scrape.api.routes import app as scrape_app

app = FastAPI(
    title="backend",
    version="0.0.0",
    description="本地资源管理器后端服务：内挂抓取/下载两个子应用",
)

app.mount("/scrape", scrape_app)
app.mount("/download", download_app)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "backend", "version": "0.0.0"}
