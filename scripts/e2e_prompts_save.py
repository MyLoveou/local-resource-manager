"""复现提示词保存失败：真起后端、真发 POST /prompts/saves。"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TOKEN = "e2e-prompts"
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"
sys.path.insert(0, str(BACKEND))

from app.shared.db.migrations import migrate  # noqa: E402


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def call(base: str, path: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "p.db"
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate(conn)
    conn.close()

    port = free_port()
    env = {**os.environ, "BACKEND_TOKEN": TOKEN, "BACKEND_DB_PATH": str(db_path),
           "PYTHONIOENCODING": "utf-8"}
    log = Path(tmp.name) / "log.txt"
    handle = log.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--no-access-log"],
        cwd=str(BACKEND), env=env, stdout=handle, stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(f"{base}/health", timeout=2)
                break
            except Exception:
                time.sleep(0.5)

        payload = {
            "title": "测试保存",
            "model": "anima",
            "positive": "masterpiece, best quality, score_7, safe, petite, full body",
            "negative": "",
            "tags": ["petite", "full body"],
            "params": {"steps": 10, "cfg": 1, "sampler": "euler", "size": "1024x1024"},
            "favorite": False,
        }
        try:
            result = call(base, "/prompts/saves", "POST", payload)
            print("保存成功:", result)
        except urllib.error.HTTPError as exc:
            print("HTTP", exc.code)
            print(exc.read().decode()[:800])
        except Exception as exc:  # noqa: BLE001
            print("异常:", type(exc).__name__, exc)

        print("=== 后端日志 ===")
        handle.flush()
        text = log.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "ERROR" in line or "Traceback" in line or "prompt" in line.lower():
                print("  " + line.strip()[:220])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        handle.close()
        tmp.cleanup()


if __name__ == "__main__":
    main()
