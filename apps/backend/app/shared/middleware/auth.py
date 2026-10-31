"""Bearer token 鉴权中间件。

- token 为空 = 未启用鉴权（开发态裸跑），启动时 lifespan 已打 WARN
- 豁免清单集中在 `shared/constants.py`：健康检查、OpenAPI 文档、图片代理
- 媒体 `/content` 使用短期 path-bound 签名，或 Bearer token
- 失败返回已完成信封的 401；日志只记 method + path，不记 token 原文
"""
from __future__ import annotations

import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from app.shared.api_envelope import error_envelope
from app.shared.config import settings
from app.shared.constants import is_auth_exempt, is_media_content_path
from app.shared.log import logger
from app.shared.media_auth import verify_media_path

UNAUTHORIZED_MESSAGE = "未授权"


def _bearer_value(request: Request) -> str:
    """取 `Authorization: Bearer <value>` 的 value；非 Bearer 返回空串。"""
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return value.strip()


def _matches(received: str, expected: str) -> bool:
    """定长比较，避免时序侧信道；先编码以容忍非 ASCII 输入。"""
    return secrets.compare_digest(received.encode("utf-8"), expected.encode("utf-8"))


async def require_token(request: Request, call_next):
    """校验 Bearer token；媒体 content 额外允许 query token。"""
    token = settings.token
    if not token:
        return await call_next(request)
    # CORS 预检（OPTIONS）按规范不携带凭证，必须放行；真正的请求仍会被校验。
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if is_auth_exempt(path):
        return await call_next(request)
    if is_media_content_path(path):
        if _matches(_bearer_value(request), token) or verify_media_path(
            path,
            request.query_params.get("exp"),
            request.query_params.get("sig"),
        ):
            return await call_next(request)
        logger.warning("拒绝未授权媒体请求 %s %s", request.method, path)
        return JSONResponse(
            status_code=401,
            content=error_envelope(UNAUTHORIZED_MESSAGE, code=401),
        )
    if not _matches(_bearer_value(request), token):
        logger.warning("拒绝未授权请求 %s %s", request.method, path)
        return JSONResponse(
            status_code=401,
            content=error_envelope(UNAUTHORIZED_MESSAGE, code=401),
        )
    return await call_next(request)
