"""Chinese-CLIP ONNX model files and downloader."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import httpx

from app.shared.config import settings

MODEL_ID = "chinese-clip-vit-base-patch16"
MODEL_NAME = "Chinese-CLIP ViT-B/16"
MODEL_DIM = 512
MODEL_FILE = "model_quantized.onnx"
TOKENIZER_FILE = "tokenizer.json"
PERSON_MODEL_FILE = "person_detector.onnx"
MODEL_BYTES = 190_842_404
TOKENIZER_BYTES = 439_124
PERSON_MODEL_BYTES = 12_823_637

_BASE_URL = "https://huggingface.co/Xenova/chinese-clip-vit-base-patch16/resolve/main"
_PERSON_URL = (
    "https://huggingface.co/salim4n/yolov8n-detect-onnx/resolve/main/"
    "yolov8n-onnx-web/yolov8n.onnx"
)
_FILES = (
    (MODEL_FILE, f"{_BASE_URL}/onnx/model_quantized.onnx", MODEL_BYTES),
    (TOKENIZER_FILE, f"{_BASE_URL}/{TOKENIZER_FILE}", TOKENIZER_BYTES),
    (PERSON_MODEL_FILE, _PERSON_URL, PERSON_MODEL_BYTES),
)

Progress = Callable[[int, int], None]


def model_dir() -> Path:
    return settings.db_path.parent / "models" / MODEL_ID


def model_path() -> Path:
    return model_dir() / MODEL_FILE


def tokenizer_path() -> Path:
    return model_dir() / TOKENIZER_FILE


def person_model_path() -> Path:
    return model_dir() / PERSON_MODEL_FILE


def is_installed() -> bool:
    return all(
        path.is_file() and path.stat().st_size > 0
        for path in (model_path(), tokenizer_path(), person_model_path())
    )


def installed_size() -> int:
    return sum(
        path.stat().st_size
        for path in (model_path(), tokenizer_path(), person_model_path())
        if path.is_file()
    )


def _read_proxy() -> str | None:
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(name)
        if value:
            return value
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enabled:
                return None
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
        if not isinstance(server, str) or not server.strip():
            return None
        parts = dict(
            item.split("=", 1) for item in server.split(";") if "=" in item
        )
        proxy = parts.get("https") or parts.get("http") or server.split(";")[0]
        if "://" not in proxy:
            proxy = f"http://{proxy}"
        return proxy
    except (OSError, ValueError, ImportError):
        return None


async def _download(
    client: httpx.AsyncClient,
    url: str,
    target: Path,
    expected: int,
    progress: Progress,
    base_done: int,
    total: int,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    part.unlink(missing_ok=True)
    done = 0
    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            content_length = int(response.headers.get("content-length") or expected)
            with part.open("wb") as handle:
                async for chunk in response.aiter_bytes(1024 * 256):
                    handle.write(chunk)
                    done += len(chunk)
                    progress(base_done + done, total or base_done + content_length)
        os.replace(part, target)
    except Exception:
        part.unlink(missing_ok=True)
        raise


async def download_model(progress: Progress) -> None:
    """Download missing model files. Progress is aggregate downloaded bytes."""
    total = MODEL_BYTES + TOKENIZER_BYTES + PERSON_MODEL_BYTES
    done = 0
    proxy = _read_proxy()
    timeout = httpx.Timeout(30.0, read=180.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(
        proxy=proxy,
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": "local-resource-manager/0.1"},
    ) as client:
        for filename, url, expected in _FILES:
            target = model_dir() / filename
            if target.is_file() and target.stat().st_size > 0:
                done += target.stat().st_size
                progress(done, total)
                continue
            await _download(client, url, target, expected, progress, done, total)
            done += target.stat().st_size
            progress(done, total)
