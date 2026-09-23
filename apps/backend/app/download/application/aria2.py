"""本机 aria2c JSON-RPC。只监听 127.0.0.1，密钥不进日志。"""

from __future__ import annotations

import asyncio
import os
import secrets
import shutil
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from app.download.application.engine import DownloadAbort, StreamResult
from app.download.application.errors import DownloadError
from app.download.application.magnet import pick_video
from app.shared.log import logger

_POLL_SECONDS = 0.4


@dataclass
class Aria2Snapshot:
    status: str
    completed: int
    total: int | None
    speed: int
    error: str | None
    files: list[Path]


class Aria2Client(Protocol):
    async def add_uri(self, uri: str, directory: Path) -> str: ...

    async def tell(self, gid: str) -> Aria2Snapshot: ...

    async def pause(self, gid: str) -> None: ...

    async def unpause(self, gid: str) -> None: ...

    async def remove(self, gid: str) -> None: ...


def find_aria2c() -> Path | None:
    override = os.environ.get("ARIA2C_PATH", "").strip().strip('"')
    if override:
        path = Path(override)
        return path if path.is_file() else None
    found = shutil.which("aria2c")
    return Path(found) if found else None


def parse_status(result: dict) -> Aria2Snapshot:
    total_raw = int(result.get("totalLength") or 0)
    files: list[Path] = []
    for item in result.get("files") or []:
        raw = item.get("path") if isinstance(item, dict) else None
        if raw:
            files.append(Path(raw))
    message = result.get("errorMessage") or None
    if message in {"", "None"}:
        message = None
    return Aria2Snapshot(
        status=str(result.get("status") or "error"),
        completed=int(result.get("completedLength") or 0),
        total=total_raw or None,
        speed=int(result.get("downloadSpeed") or 0),
        error=message,
        files=files,
    )


class Aria2Daemon:
    def __init__(self, binary: Path) -> None:
        self.binary = binary
        self._secret = secrets.token_hex(16)
        self._proc: asyncio.subprocess.Process | None = None
        self._http: httpx.AsyncClient | None = None
        self._url = ""

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def start(self) -> None:
        port = _free_port()
        self._proc = await asyncio.create_subprocess_exec(
            str(self.binary),
            "--enable-rpc=true",
            "--rpc-listen-all=false",
            f"--rpc-listen-port={port}",
            f"--rpc-secret={self._secret}",
            "--seed-time=0",
            "--bt-enable-lpd=false",
            "--console-log-level=warn",
            "--summary-interval=0",
            "--quiet=true",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._url = f"http://127.0.0.1:{port}/jsonrpc"
        self._http = httpx.AsyncClient(timeout=30.0)
        for _ in range(50):
            if self._proc.returncode is not None:
                raise DownloadError("aria2 启动失败", 500)
            try:
                await self._rpc("aria2.getVersion")
                return
            except (httpx.HTTPError, DownloadError):
                await asyncio.sleep(0.1)
        raise DownloadError("aria2 无响应", 500)

    async def shutdown(self) -> None:
        try:
            if self.alive:
                await self._rpc("aria2.shutdown")
        except (httpx.HTTPError, DownloadError):
            logger.warning("aria2 未能正常退出")
        if self._proc is not None and self._proc.returncode is None:
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=3)
            except TimeoutError:
                self._proc.kill()
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def add_uri(self, uri: str, directory: Path) -> str:
        directory.mkdir(parents=True, exist_ok=True)
        gid = await self._rpc(
            "aria2.addUri",
            [uri],
            {"dir": str(directory), "seed-time": "0"},
        )
        return str(gid)

    async def tell(self, gid: str) -> Aria2Snapshot:
        result = await self._rpc("aria2.tellStatus", gid)
        if not isinstance(result, dict):
            raise DownloadError("aria2 状态无效", 502)
        return parse_status(result)

    async def pause(self, gid: str) -> None:
        try:
            await self._rpc("aria2.forcePause", gid)
        except DownloadError:
            logger.info("aria2 暂停被忽略 gid=%s", gid)

    async def unpause(self, gid: str) -> None:
        await self._rpc("aria2.unpause", gid)

    async def remove(self, gid: str) -> None:
        try:
            await self._rpc("aria2.forceRemove", gid)
        except DownloadError:
            logger.info("aria2 移除被忽略 gid=%s", gid)

    async def _rpc(self, method: str, *params: object) -> object:
        if self._http is None:
            raise DownloadError("aria2 未启动", 500)
        payload = {
            "jsonrpc": "2.0",
            "id": "sm",
            "method": method,
            "params": [f"token:{self._secret}", *params],
        }
        response = await self._http.post(self._url, json=payload)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            message = body["error"].get("message") if isinstance(body["error"], dict) else "aria2 调用失败"
            raise DownloadError(str(message or "aria2 调用失败"), 502)
        return body.get("result")


_daemon: Aria2Daemon | None = None


async def daemon() -> Aria2Daemon:
    global _daemon
    if _daemon is not None and _daemon.alive:
        return _daemon
    binary = find_aria2c()
    if binary is None:
        raise DownloadError("未找到 aria2，无法下载磁力", 400)
    created = Aria2Daemon(binary)
    await created.start()
    _daemon = created
    return created


async def shutdown_aria2() -> None:
    global _daemon
    current = _daemon
    _daemon = None
    if current is not None:
        await current.shutdown()


async def remove_magnet(gid: str) -> None:
    if _daemon is None or not _daemon.alive:
        return
    await _daemon.remove(gid)


async def pull_magnet(
    magnet: str,
    dest: Path,
    *,
    existing_gid: str | None = None,
    on_progress=None,
    should_abort=None,
    on_gid=None,
    client: Aria2Client | None = None,
) -> tuple[StreamResult, str]:
    session = client or await daemon()
    gid = existing_gid
    if gid is None:
        gid = await session.add_uri(magnet, dest)
    else:
        try:
            await session.unpause(gid)
        except DownloadError:
            gid = await session.add_uri(magnet, dest)
    if on_gid is not None:
        on_gid(gid)
    while True:
        signal = await should_abort() if should_abort is not None else None
        if signal == "paused":
            await session.pause(gid)
            abort = DownloadAbort("paused")
            abort.gid = gid
            raise abort
        if signal:
            await session.remove(gid)
            raise DownloadAbort(signal)
        snap = await session.tell(gid)
        if on_progress is not None:
            await on_progress(snap.completed, snap.total, snap.speed)
        if snap.status == "complete":
            video = pick_video(dest, snap.files)
            return StreamResult(video, video.name, video.stat().st_size, snap.total), gid
        if snap.status in {"error", "removed"}:
            await session.remove(gid)
            raise DownloadError(snap.error or "磁力下载失败", 502)
        await asyncio.sleep(_POLL_SECONDS)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
