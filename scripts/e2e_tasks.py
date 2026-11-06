"""任务 API 的端到端冒烟：真起后端、真走 HTTP、真读数据库。

不是单测：它会 spawn 一个 uvicorn 进程，用固定 token 调 /tasks，
再直接查 sqlite 确认状态真的落库。运行：

    apps/backend/.venv/Scripts/python.exe scripts/e2e_tasks.py
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

TOKEN = "e2e-token"
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "backend"
PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def call(base: str, path: str, method: str = "GET") -> dict:
    req = urllib.request.Request(f"{base}{path}", method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def wait_health(base: str, timeout: float = 40.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.5)
    raise SystemExit("后端没有起来")


def main() -> None:
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "e2e.db"
    port = free_port()
    env = {
        **os.environ,
        "BACKEND_TOKEN": TOKEN,
        "BACKEND_DB_PATH": str(db_path),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--no-access-log"],
        cwd=str(BACKEND),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        wait_health(base)

        # 1) 未授权必须 401
        try:
            urllib.request.urlopen(f"{base}/tasks", timeout=5)
            raise SystemExit("FAIL: 未授权居然成功了")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401, exc.code
            print("PASS 未授权 → 401")

        # 2) 空任务列表
        payload = call(base, "/tasks")
        assert payload["data"]["items"] == [], payload
        print("PASS 空列表")

        # 3) 直接写一行任务，验证 API 能读出来（含中文标题）
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO tasks (id, kind, title, state, done, total, percent, attempts, created_at)"
            " VALUES ('t1', 'scrape', '刮削 · 只有神知道的世界', 'running', 3, 10, 30, 1, datetime('now'))"
        )
        conn.commit()
        conn.close()

        items = call(base, "/tasks?active=1")["data"]["items"]
        assert len(items) == 1 and items[0]["title"].startswith("刮削"), items
        assert items[0]["percent"] == 30
        print("PASS active=1 返回运行中任务，进度 30%")

        # 4) 取消
        cancelled = call(base, "/tasks/t1/cancel", method="POST")["data"]
        assert cancelled["state"] == "cancelled", cancelled
        print("PASS 取消 → cancelled")

        # 5) 已结束的任务不能再取消（409）
        try:
            call(base, "/tasks/t1/cancel", method="POST")
            raise SystemExit("FAIL: 重复取消没有报错")
        except urllib.error.HTTPError as exc:
            assert exc.code == 409, exc.code
            print("PASS 重复取消 → 409")

        # 6) 重试改回 queued
        retried = call(base, "/tasks/t1/retry", method="POST")["data"]
        assert retried["state"] == "queued", retried
        print("PASS 重试 → queued")

        # 7) 导入重试被拒绝
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO tasks (id, kind, title, state, created_at)"
            " VALUES ('t2', 'import', '导入 · 番剧', 'interrupted', datetime('now'))"
        )
        conn.commit()
        conn.close()
        try:
            call(base, "/tasks/t2/retry", method="POST")
            raise SystemExit("FAIL: 导入重试不应通过")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400, exc.code
            print("PASS 导入重试 → 400（需走继续导入）")

        print("\n全部通过")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(0.5)
        tmp.cleanup()


if __name__ == "__main__":
    sys.exit(main())
