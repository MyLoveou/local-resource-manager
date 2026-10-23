# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir 打包描述：后端 exe + 随包 migrations。"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

BACKEND = Path(SPECPATH).parent

# Conda 发行版把 OpenSSL/ffi/sqlite 等运行库放在 Library/bin（PyInstaller 默认不收集）
binaries, datas, hiddenimports = [], [], []
for package in ("onnxruntime", "tokenizers"):
    _datas, _binaries, _hidden = collect_all(package)
    datas += _datas
    binaries += _binaries
    hiddenimports += _hidden
_conda_bin = Path(sys.base_prefix) / "Library" / "bin"
for _name in (
    "libssl-3-x64.dll",
    "libcrypto-3-x64.dll",
    "ffi.dll",
    "sqlite3.dll",
    "liblzma.dll",
    "LIBBZ2.dll",
    "libexpat.dll",
    "libmpdec-4.dll",
    "zstd.dll",
):
    _dll = _conda_bin / _name
    if _dll.exists():
        binaries.append((str(_dll), "."))

a = Analysis(
    [str(BACKEND / "run_server.py")],
    pathex=[str(BACKEND)],
    binaries=binaries,
    datas=datas + [
        (
            str(BACKEND / "app" / "shared" / "db" / "migrations"),
            "app/shared/db/migrations",
        )
    ],
    hiddenimports=hiddenimports + [
        # uvicorn 动态导入的 loop/protocol/lifespan 实现
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan.on",
        # SQLAlchemy async + aiosqlite
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "aiosqlite",
        # 监视
        "watchdog.observers.polling",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="source-manager-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="source-manager-backend",
)
