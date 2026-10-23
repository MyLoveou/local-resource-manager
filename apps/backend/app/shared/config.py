"""应用配置。"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/backend 目录（相对本文件向上两级）
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
# apps/ 目录
APPS_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """后端服务共享配置。"""

    # 环境变量前缀：BACKEND_TOKEN / BACKEND_HOST / BACKEND_PORT / BACKEND_DB_PATH …
    # 桌面主进程按 BACKEND_TOKEN 注入，故此处必须有前缀，否则字段名 token 读的是 TOKEN。
    model_config = SettingsConfigDict(env_prefix="BACKEND_")

    host: str = "127.0.0.1"
    port: int = 8000
    token: str = ""  # 进程间鉴权 token；为空表示未启用鉴权（见 shared/middleware/auth.py）
    db_path: Path = BACKEND_DIR / "data" / "library.db"  # SQLite 单文件
    # CORS 允许源：本地服务绑定 127.0.0.1 + token 鉴权（非 cookie），"*" 安全
    # 覆盖开发态 vite(localhost:5173) 与生产态 Electron(file:///app://) 源

    cors_origins: list[str] = ["*"]
    # 常驻监视：资源类型("image"/"video"…) → 源目录列表；一个类型可多个目录，同一目录可多类型。
    # env 用 JSON 对象：BACKEND_WATCH_DIRS='{"image":["D:\\Pics"],"video":["D:\\Videos","E:\\Videos"]}'
    watch_dirs: dict[str, list[str]] = {}
    # 可选本地 VLM：Ollama 地址、默认视觉模型与超时。
    vlm_url: str = "http://127.0.0.1:11434"
    vlm_model: str = "qwen2.5vl:3b"
    vlm_timeout: int = 120
    vlm_bin: str = ""
    vlm_models_dir: str = ""


def resolve_log_dir() -> Path:
    """与桌面端 getLogDir 对齐：LOG_DIR 优先，否则 apps/logs。"""
    env = os.environ.get("LOG_DIR")
    if env:
        return Path(env)
    return APPS_DIR / "logs"


class LoggingConfig:
    # 与桌面端 electron-log 统一：
    # YYYY-MM-DD HH:mm:ss - [scope] - LEVEL - message
    log_level: str = "INFO"
    log_file_max_size: int = 10 * 1024 * 1024  # 10MB
    log_file_backup_count: int = 5
    log_file_encoding: str = "utf-8"
    log_file_format: str = "%(asctime)s - [backend] - %(levelname)s - %(message)s"
    log_file_datefmt: str = "%Y-%m-%d %H:%M:%S"
    log_file_level: str = "INFO"

    @staticmethod
    def log_dir() -> Path:
        return resolve_log_dir()

    @staticmethod
    def log_file() -> Path:
        return resolve_log_dir() / "backend.log"

    @staticmethod
    def log_file_error() -> Path:
        return resolve_log_dir() / "backend.error.log"


settings = Settings()
