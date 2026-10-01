"""Bearer token 鉴权中间件。

- token 为空 = 未启用鉴权（开发态裸跑），启动时 lifespan 已打 WARN
- 豁免清单集中在 `shared/constants.py`：健康检查、OpenAPI 文档、媒体字节流
- 失败返回已完成信封的 401；日志只记 method + path，不记 token 原文
"""
from __future__ import annotations

import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from app.shared.api_envelope import error_envelope
from app.shared.config import settings
from app.shared.constants import is_auth_exempt
from app.shared.log import logger

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
    """校验 Bearer token；token 未配置或路径命中豁免则直接放行。"""
    token = settings.token
    if not token:
        return await call_next(request)
    # CORS 预检（OPTIONS）按规范不携带凭证，必须放行；真正的请求仍会被校验。
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if is_auth_exempt(path):
        return await call_next(request)
    if not _matches(_bearer_value(request), token):
        logger.warning("拒绝未授权请求 %s %s", request.method, path)
        return JSONResponse(
            status_code=401,
            content=error_envelope(UNAUTHORIZED_MESSAGE, code=401),
        )
    return await call_next(request)
