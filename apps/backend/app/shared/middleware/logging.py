"""HTTP 访问日志。中间件只记 status；响应体在路由/用例里打（见 library overview）。"""
from fastapi import Request

from ..log import logger


async def log_requests(request: Request, call_next):
    path = request.url.path
    quiet = path.endswith("/content")
    if not quiet:
        logger.info("Request: %s %s", request.method, path)
    response = await call_next(request)
    if not quiet:
        logger.info("Response: %s %s -> %s", request.method, path, response.status_code)
    return response
