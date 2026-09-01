import logging
import logging.handlers
import threading

from app.shared.config import LoggingConfig


class LoggingApp:
    """应用日志：进程内只配置一次，对外使用模块级 logger。"""

    _configured = False
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.logger = logging.getLogger("backend")

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

    def _add_file_handler(self) -> None:
        handler = logging.handlers.RotatingFileHandler(
            filename=LoggingConfig.log_file(),
            maxBytes=LoggingConfig.log_file_max_size,
            backupCount=LoggingConfig.log_file_backup_count,
            encoding=LoggingConfig.log_file_encoding,
        )
        handler.setLevel(self._level(LoggingConfig.log_file_level))
        handler.setFormatter(self._formatter())
        self.logger.addHandler(handler)

    def _add_error_handler(self) -> None:
        handler = logging.handlers.RotatingFileHandler(
            filename=LoggingConfig.log_file_error(),
            maxBytes=LoggingConfig.log_file_max_size,
            backupCount=LoggingConfig.log_file_backup_count,
            encoding=LoggingConfig.log_file_encoding,
        )
        handler.setLevel(logging.ERROR)
        handler.setFormatter(self._formatter())
        self.logger.addHandler(handler)

    def get_logger(self) -> logging.Logger:
        if LoggingApp._configured:
            return self.logger
        with LoggingApp._lock:
            if LoggingApp._configured:
                return self.logger
            self.logger.setLevel(self._level(LoggingConfig.log_level))
            self.logger.propagate = False
            self._ensure_log_dir()
            self._add_console_handler()
            self._add_file_handler()
            self._add_error_handler()
            LoggingApp._configured = True
        return self.logger


logger = LoggingApp().get_logger()
