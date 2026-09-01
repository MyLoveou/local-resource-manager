"""应用配置。"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings

# apps/backend 目录（相对本文件向上两级）
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
# apps/ 目录
APPS_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """后端服务共享配置。"""

    host: str = "127.0.0.1"
    port: int = 8000
    token: str = ""  # 后续：进程间鉴权 token
    db_path: Path = BACKEND_DIR / "data" / "library.db"  # SQLite 单文件
    # CORS 允许源：本地服务绑定 127.0.0.1 + token 鉴权（非 cookie），"*" 安全
    # 覆盖开发态 vite(localhost:5173) 与生产态 Electron(file:///app://) 源

    cors_origins: list[str] = ["*"]


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
