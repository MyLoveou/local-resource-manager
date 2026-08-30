from fastapi import FastAPI

app = FastAPI(
    title="scrape-app",
    version="0.0.0",
    description="抓取应用：SearXNG 检索 + 站点适配器抓取详情",
    root_path="/scrape",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "scrape", "version": "0.0.0"}
