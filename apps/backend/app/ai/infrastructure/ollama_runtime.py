"""Detect and start a local Ollama runtime without requiring a bundled server."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path

import httpx

from app.shared.config import settings


def _common_binaries() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        raw = os.environ.get(env_name)
        if not raw:
            continue
        root = Path(raw)
        candidates.extend(
            [
                root / "Programs" / "Ollama" / "ollama.exe",
                root / "Ollama" / "ollama.exe",
            ]
        )
    candidates.append(Path("ollama.exe"))
    return candidates


def detect_binary(preferred: str = "") -> str | None:
    for raw in (preferred, settings.vlm_bin):
        if not raw:
            continue
        path = Path(raw).expanduser()
        if path.is_file():
            return str(path.resolve())
    found = shutil.which("ollama")
    if found:
        return found
    for path in _common_binaries():
        try:
            if path.is_file():
                return str(path.resolve())
        except OSError:
            continue
    return None


def resolve_models_dir(binary: str = "") -> str:
    if settings.vlm_models_dir:
        return settings.vlm_models_dir
    inherited = os.environ.get("OLLAMA_MODELS", "")
    if inherited:
        return inherited
    if binary:
        sibling = Path(binary).expanduser().resolve().parent.parent / "models"
        if sibling.is_dir():
            return str(sibling)
    return ""


def _host_from_url() -> str:
    raw = settings.vlm_url.strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    return raw.split("/", 1)[0] or "127.0.0.1:11434"


async def is_running() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{settings.vlm_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            return True
    except Exception:
        return False


async def runtime_status(preferred_binary: str = "") -> dict:
    binary = detect_binary(preferred_binary)
    running = await is_running()
    return {
        "running": running,
        "url": settings.vlm_url,
        "binary_path": binary or "",
        "detected": binary is not None,
        "models_dir": resolve_models_dir(binary or ""),
        "error": "",
    }


async def start_runtime(binary: str) -> dict:
    if await is_running():
        return await runtime_status(binary)
    if not binary:
        raise RuntimeError("未检测到 Ollama，请先安装或选择 ollama.exe")
    path = Path(binary).expanduser()
    if not path.is_file():
        raise RuntimeError(f"Ollama 程序不存在：{path}")

    env = os.environ.copy()
    env["OLLAMA_HOST"] = _host_from_url()
    models_dir = resolve_models_dir(str(path))
    if models_dir:
        env["OLLAMA_MODELS"] = models_dir
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [str(path), "serve"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        creationflags=creationflags,
    )
    for _ in range(50):
        if process.poll() is not None:
            output = ""
            if process.stdout is not None:
                output = process.stdout.read(2000).strip()
            raise RuntimeError(
                "Ollama 启动失败" + (f"：{output}" if output else "，请检查安装路径或端口是否被占用")
            )
        if await is_running():
            return await runtime_status(str(path))
        await asyncio.sleep(0.2)
    process.terminate()
    raise RuntimeError("Ollama 启动超时，请检查端口 11434 或手动运行 ollama serve")


def install_help_url() -> str:
    return "https://ollama.com/download/windows"
