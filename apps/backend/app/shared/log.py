import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from app.shared.config import LoggingConfig


class DailyFileHandler(logging.Handler):
    """Write to prefix-YYYY-MM-DD.log and prune old daily files."""

    def __init__(
        self,
        directory: Path,
        prefix: str,
        level: int,
        *,
        encoding: str = "utf-8",
        retention_days: int = 14,
    ) -> None:
        super().__init__(level)
        self.directory = directory
        self.prefix = prefix
        self.encoding = encoding
        self.retention_days = retention_days
        self._stream = None
        self._date = ""

    def _path_for(self, day: str) -> Path:
        return self.directory / f"{self.prefix}-{day}.log"

    def _open_for(self, day: str) -> None:
        if self._stream is not None:
            self._stream.close()
        self._date = day
        self._stream = self._path_for(day).open(
            "a", encoding=self.encoding, buffering=1
        )
        self._prune(day)

    def _prune(self, today: str) -> None:
        cutoff = time.time() - self.retention_days * 86400
        for path in self.directory.glob(f"{self.prefix}-*.log"):
            try:
                if path.name == f"{self.prefix}-{today}.log":
                    continue
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            day = datetime.now().strftime("%Y-%m-%d")
            if self._stream is None or day != self._date:
                self._open_for(day)
            assert self._stream is not None
            self._stream.write(self.format(record) + "\n")
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        super().close()


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

    def _daily_handler(self, prefix: str, level: int) -> logging.Handler:
        handler = DailyFileHandler(
            LoggingConfig.log_dir(),
            prefix,
            level,
            encoding=LoggingConfig.log_file_encoding,
            retention_days=LoggingConfig.log_retention_days,
        )
        handler.setFormatter(self._formatter())
        return handler

    def _prune_legacy_logs(self) -> None:
        cutoff = time.time() - LoggingConfig.log_retention_days * 86400
        for pattern in (
            "backend.log",
            "backend.error.log",
            "operations.log",
            "backend.log.*",
            "backend.error.log.*",
            "operations.log.*",
        ):
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
            self._prune_legacy_logs()
            self._add_console_handler()
            self.logger.addHandler(
                self._daily_handler(
                    "backend",
                    self._level(LoggingConfig.log_file_level),
                )
            )
            self.logger.addHandler(self._daily_handler("backend.error", logging.ERROR))
            self.operation_logger.addHandler(
                self._daily_handler("operations", logging.INFO)
            )
            LoggingApp._configured = True
        return self.logger


logger = LoggingApp().get_logger()
operations_logger = logging.getLogger("backend.operations")
