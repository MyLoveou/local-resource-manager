import logging
import logging.handlers
import threading
import time
from pathlib import Path

from app.shared.config import LoggingConfig


class LoggingApp:
    """Configure backend and operation logs with daily retention."""

    _configured = False
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.logger = logging.getLogger("backend")
        self.operation_logger = logging.getLogger("backend.operations")

    def _level(self, name: str) -> int:
        level = getattr(logging, name.upper(), None)
        if not isinstance(level, int):
            return logging.INFO
        return level

    def _formatter(self) -> logging.Formatter:
        return logging.Formatter(
            LoggingConfig.log_file_format,
            datefmt=LoggingConfig.log_file_datefmt,
        )

    def _ensure_log_dir(self) -> None:
        LoggingConfig.log_dir().mkdir(parents=True, exist_ok=True)

    def _add_console_handler(self) -> None:
        handler = logging.StreamHandler()
        handler.setLevel(self._level(LoggingConfig.log_level))
        handler.setFormatter(self._formatter())
        self.logger.addHandler(handler)

    def _daily_handler(self, filename: Path, level: int) -> logging.Handler:
        handler = logging.handlers.TimedRotatingFileHandler(
            filename=filename,
            when="midnight",
            interval=1,
            backupCount=LoggingConfig.log_retention_days,
            encoding=LoggingConfig.log_file_encoding,
            delay=True,
            utc=False,
        )
        handler.suffix = "%Y-%m-%d"
        handler.setLevel(level)
        handler.setFormatter(self._formatter())
        return handler

    def _prune_old_logs(self) -> None:
        cutoff = time.time() - LoggingConfig.log_retention_days * 86400
        for pattern in ("backend.log.*", "backend.error.log.*", "operations.log.*"):
            for path in LoggingConfig.log_dir().glob(pattern):
                try:
                    if path.is_file() and path.stat().st_mtime < cutoff:
                        path.unlink()
                except OSError:
                    pass

    def get_logger(self) -> logging.Logger:
        if LoggingApp._configured:
            return self.logger
        with LoggingApp._lock:
            if LoggingApp._configured:
                return self.logger
            self.logger.setLevel(self._level(LoggingConfig.log_level))
            self.logger.propagate = False
            self.operation_logger.setLevel(logging.INFO)
            self.operation_logger.propagate = False
            self._ensure_log_dir()
            self._prune_old_logs()
            self._add_console_handler()
            self.logger.addHandler(
                self._daily_handler(
                    LoggingConfig.log_file(),
                    self._level(LoggingConfig.log_file_level),
                )
            )
            self.logger.addHandler(
                self._daily_handler(LoggingConfig.log_file_error(), logging.ERROR)
            )
            self.operation_logger.addHandler(
                self._daily_handler(LoggingConfig.operation_log_file(), logging.INFO)
            )
            LoggingApp._configured = True
        return self.logger


logger = LoggingApp().get_logger()
operations_logger = logging.getLogger("backend.operations")
