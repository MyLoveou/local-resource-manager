"""Shared AI application errors."""

from __future__ import annotations


class AIServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code
