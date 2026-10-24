"""Conservative local hardware hints for AI caption concurrency."""

from __future__ import annotations

import ctypes
import os
import platform
import subprocess
from pathlib import Path

_GIB = 1024**3
_cache: tuple[float, dict] | None = None


def _windows_memory() -> tuple[int, int]:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return int(status.ullTotalPhys), int(status.ullAvailPhys)
    return 0, 0


def _unix_memory() -> tuple[int, int]:
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, raw = line.partition(":")
            if raw.strip().endswith("kB"):
                values[key] = int(raw.split()[0]) * 1024
        return values.get("MemTotal", 0), values.get("MemAvailable", 0)
    except OSError:
        return 0, 0


def _gpu_info() -> dict:
    if not shutil_which("nvidia-smi"):
        return {}
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        line = next((row.strip() for row in result.stdout.splitlines() if row.strip()), "")
        if not line:
            return {}
        name, total, free = [part.strip() for part in line.split(",", 2)]
        return {
            "gpu_name": name,
            "vram_total_bytes": int(float(total)) * 1024 * 1024,
            "vram_free_bytes": int(float(free)) * 1024 * 1024,
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def shutil_which(command: str) -> str | None:
    import shutil

    return shutil.which(command)


def device_info() -> dict:
    global _cache
    import time

    now = time.monotonic()
    if _cache is not None and now - _cache[0] < 30:
        return _cache[1]
    total, available = (_windows_memory() if os.name == "nt" else _unix_memory())
    info = {
        "cpu_count": os.cpu_count() or 1,
        "memory_total_bytes": total,
        "memory_available_bytes": available,
        "gpu_name": "",
        "vram_total_bytes": 0,
        "vram_free_bytes": 0,
        "platform": platform.platform(),
    }
    info.update(_gpu_info())
    _cache = (now, info)
    return info


def recommendation(info: dict | None = None) -> dict[str, int]:
    """Return conservative concurrency values, never more than 3."""
    value = info or device_info()
    if value.get("vram_total_bytes"):
        total = int(value.get("vram_total_bytes") or 0)
        # Use total VRAM for the tier: the currently loaded model can make
        # "free" look tiny even when a second request can be served.
        if total >= 10 * _GIB:
            return {"safe": 1, "balanced": 2, "max": 2}
        if total >= 7 * _GIB:
            return {"safe": 1, "balanced": 2, "max": 2}
        if total >= 5 * _GIB:
            return {"safe": 1, "balanced": 1, "max": 2}
        return {"safe": 1, "balanced": 1, "max": 1}
    cpu = int(value.get("cpu_count") or 1)
    memory = int(value.get("memory_available_bytes") or 0)
    if cpu >= 8 and memory >= 8 * _GIB:
        return {"safe": 1, "balanced": 1, "max": 2}
    return {"safe": 1, "balanced": 1, "max": 1}
