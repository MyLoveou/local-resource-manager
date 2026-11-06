"""冻结后端入口（PyInstaller onedir）：参数与主进程 spawn 约定一致。"""

from __future__ import annotations

import argparse

import uvicorn

from app.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="local resource manager backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-access-log", action="store_true")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, access_log=not args.no_access_log)


if __name__ == "__main__":
    main()
