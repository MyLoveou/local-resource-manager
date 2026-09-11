"""JSON 响应信封：code / status / message / data。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse, Response, StreamingResponse

from app.shared.constants import (
    API_CODE_OK,
    API_MESSAGE_OK,
    API_STATUS_ERROR,
    API_STATUS_SUCCESS,
    ENVELOPE_SKIP_PATHS,
)
from app.shared.log import logger


def success_envelope(data: Any, *, message: str = API_MESSAGE_OK, code: int = API_CODE_OK) -> dict[str, Any]:
    """成功响应体。"""
    return {
        "code": code,
        "status": API_STATUS_SUCCESS,
        "message": message,
        "data": jsonable_encoder(data),
    }


def error_envelope(
    message: str,
    *,
    code: int,
    data: Any = None,
) -> dict[str, Any]:
    """失败响应体。code 与 HTTP 状态对齐。"""
    return {
        "code": code,
        "status": API_STATUS_ERROR,
        "message": message,
        "data": jsonable_encoder(data),
    }


def is_envelope(payload: Any) -> bool:
    """是否已是信封，避免二次包装。"""
    if not isinstance(payload, dict):
        return False
    return (
        isinstance(payload.get("code"), int)
        and payload.get("status") in (API_STATUS_SUCCESS, API_STATUS_ERROR)
        and isinstance(payload.get("message"), str)
        and "data" in payload
    )


def _should_skip(request: Request, response: Response) -> bool:
    path = request.url.path
    if path in ENVELOPE_SKIP_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
        return True
    if isinstance(response, (FileResponse, StreamingResponse)):
        return True
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return True
    if response.status_code == 204:
        return True
    return False


async def _read_body(response: Response) -> bytes:
    body = getattr(response, "body", b"") or b""
    if body:
        return body
    chunks: list[bytes] = []
    iterator = getattr(response, "body_iterator", None)
    if iterator is None:
        return b""
    async for chunk in iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
    return b"".join(chunks)


_SKIP_COPY_HEADERS = frozenset(
    {"content-length", "content-type", "transfer-encoding", "content-encoding"}
)


def _json_response(
    payload: dict[str, Any],
    status_code: int,
    *,
    headers: Any = None,
) -> JSONResponse:
    response = JSONResponse(content=payload, status_code=status_code)
    if headers:
        for key, value in headers.items():
            if key.lower() in _SKIP_COPY_HEADERS:
                continue
            response.headers[key] = value
    return response


async def wrap_json_envelope(request: Request, call_next):
    """把 JSON 业务体包进信封；文件流与 OpenAPI 文档不包。"""
    response = await call_next(request)
    if _should_skip(request, response):
        return response
    raw = await _read_body(response)
    if not raw:
        return response
    try:
        payload = json.loads(raw)
    except ValueError:
        rebuilt = Response(content=raw, status_code=response.status_code, media_type=response.media_type)
        for key, value in response.headers.items():
            if key.lower() in _SKIP_COPY_HEADERS:
                continue
            rebuilt.headers[key] = value
        return rebuilt
    headers = response.headers
    if is_envelope(payload):
        return _json_response(payload, response.status_code, headers=headers)
    if response.status_code >= 400:
        message = "error"
        data: Any = payload
        if isinstance(payload, dict) and "detail" in payload:
            detail = payload["detail"]
            message = detail if isinstance(detail, str) else "error"
            data = None if isinstance(detail, str) else detail
        return _json_response(
            error_envelope(message, code=response.status_code, data=data),
            response.status_code,
            headers=headers,
        )
    return _json_response(success_envelope(payload), response.status_code, headers=headers)


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    headers = exc.headers
    if isinstance(detail, str):
        return _json_response(error_envelope(detail, code=exc.status_code), exc.status_code, headers=headers)
    return _json_response(
        error_envelope("error", code=exc.status_code, data=detail),
        exc.status_code,
        headers=headers,
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return _json_response(
        error_envelope("validation error", code=422, data=exc.errors()),
        422,
    )


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常: %s", exc)
    return _json_response(error_envelope("internal error", code=500), 500)
