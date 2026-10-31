"""Windows 系统代理 → httpx 能识别的环境变量。

后端是 Electron 拉起的独立进程，不继承 Windows 的"系统代理"设置；httpx 只读
`HTTP_PROXY` / `HTTPS_PROXY`（`trust_env` 默认开启）。番剧、TMDB 这类境外站点
不走代理会直接 ConnectError，所以启动时读一次注册表注入到进程环境。

显式配置了 `HTTPS_PROXY` 的用户优先，不会被覆盖。
"""

from __future__ import annotations

import os
import sys

from app.shared.log import logger

_INTERNET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
_BYPASS_HOSTS = "127.0.0.1,localhost,::1"


def _windows_proxy() -> str | None:
    """读取当前用户的系统代理；未启用或读不到返回 None。"""
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except ImportError:  # pragma: no cover - 非 Windows 解释器
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _INTERNET_SETTINGS) as key:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except OSError:
        return None
    if not enabled or not server:
        return None
    text = str(server).strip()
    if "=" in text:
        # 分协议写法：http=host:port;https=host:port
        parts = dict(item.split("=", 1) for item in text.split(";") if "=" in item)
        text = (parts.get("https") or parts.get("http") or "").strip()
    if not text:
        return None
    if "://" not in text:
        text = f"http://{text}"
    return text


def apply_system_proxy() -> str | None:
    """把系统代理写进进程环境，返回生效的代理地址（None 表示不走代理）。"""
    current = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if current:
        return current
    proxy = _windows_proxy()
    if not proxy:
        return None
    os.environ.setdefault("HTTP_PROXY", proxy)
    os.environ.setdefault("HTTPS_PROXY", proxy)
    os.environ.setdefault("http_proxy", proxy)
    os.environ.setdefault("https_proxy", proxy)
    existing = os.environ.get("NO_PROXY", "")
    os.environ["NO_PROXY"] = ",".join([p for p in (existing, _BYPASS_HOSTS) if p])
    logger.info("已按系统设置启用代理 %s", proxy)
    return proxy
