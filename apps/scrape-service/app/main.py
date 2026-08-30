from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="scrape-service",
    version="0.0.0",
    description="元数据抓取服务：SearXNG 检索 + 站点适配器抓取详情",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "scrape", "version": "0.0.0"}
