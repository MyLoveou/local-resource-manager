from fastapi import FastAPI

app = FastAPI(
    title="download-app",
    version="0.0.0",
    description="下载应用：编排层 + aria2c/rqbit 双引擎 + yt-dlp 站点兜底",
    root_path="/download",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "download", "version": "0.0.0"}
