"""文本模型（本地 Ollama）的极简补全客户端。

只服务一件事：把一句指令发过去、拿回纯文本。任何失败都返回 None——调用方据此降级，
不要把"模型不可用"变成异常往上抛。
"""

from __future__ import annotations

import os

import httpx

from app.shared.config import settings
from app.shared.log import logger

DEFAULT_TIMEOUT = 20.0


def _testing() -> bool:
    """pytest 下不连真实模型：测试不该依赖本机是否开着 Ollama（见经验 29）。"""
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


async def complete(prompt: str, *, timeout: float = DEFAULT_TIMEOUT) -> str | None:
    """调用 Ollama /api/generate；不可用或异常返回 None。"""
    if _testing():
        return None
    base = (settings.vlm_url or "").rstrip("/")
    if not base:
        return None
    payload = {
        "model": settings.vlm_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{base}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # noqa: BLE001 - 模型不可用不是错误，是降级
        logger.info("文本模型不可用，跳过 AI 兜底: %s", type(exc).__name__)
        return None
    text = data.get("response")
    return str(text) if isinstance(text, str) and text.strip() else None
