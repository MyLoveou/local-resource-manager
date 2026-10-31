"""HTTP / API 横切常量（单一事实源）。

领域枚举已按限界上下文归位：
- SourceKind → app.library.domain.models
- AdapterKey → app.settings.domain.models
- 下载域枚举已随下载功能移除（D-20261007-01）
"""
API_CODE_OK = 0
API_STATUS_SUCCESS = "success"
API_STATUS_ERROR = "error"
API_MESSAGE_OK = "ok"

ENVELOPE_SKIP_PATHS = ("/docs", "/redoc", "/openapi.json")

# 鉴权豁免：健康检查（/health 与各子应用 /xxx/health）、OpenAPI 文档、
# 媒体字节流（img / video / model-viewer 无法带请求头）
AUTH_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json")
AUTH_EXEMPT_SUFFIXES = ("/health",)
AUTH_EXEMPT_PATHS = ("/scrape/proxy-image",)


def is_auth_exempt(path: str) -> bool:
    """该路径是否免 token 校验（清单集中在本文，不在路由里写条件）。"""
    if path in AUTH_EXEMPT_PATHS:
        return True
    if path.startswith(AUTH_EXEMPT_PREFIXES):
        return True
    return path.endswith(AUTH_EXEMPT_SUFFIXES)


def is_media_content_path(path: str) -> bool:
    """/content 仍需 token；img/video 通过查询参数携带 token。"""
    return path.endswith("/content")
