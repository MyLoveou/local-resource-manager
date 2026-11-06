"""完整刮削流程演练：真起后端、真发搜索、真等结果，并打印后端日志。

用法：
    apps/backend/.venv/Scripts/python.exe scripts/e2e_scrape.py "只有神知道的世界"
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

TOKEN = "e2e-scrape"
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
    query = sys.argv[1] if len(sys.argv) > 1 else "只有神知道的世界"
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db_path = Path(tmp.name) / "scrape.db"
    log_path = Path(tmp.name) / "backend.log"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate(conn)
    conn.execute(
        "INSERT INTO resources (id, type, title, status, created_at, updated_at)"
        " VALUES (1, 'anime', ?, 'active', datetime('now'), datetime('now'))",
        (query,),
    )
    conn.commit()
    conn.close()

    port = free_port()
    env = {
        **os.environ,
        "BACKEND_TOKEN": TOKEN,
        "BACKEND_DB_PATH": str(db_path),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    log_file = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--no-access-log"],
        cwd=str(BACKEND),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        wait_health(base)
        print(f"后端就绪 :{port}，查询词：{query}")

        started = time.time()
        job = call(base, "/scrape/jobs", "POST", {"resourceId": 1, "query": query})["data"]
        job_id = job["id"]
        print(f"job={job_id} 状态={job['status']}")

        while True:
            time.sleep(1.0)
            current = call(base, f"/scrape/jobs/{job_id}")["data"]
            elapsed = time.time() - started
            if current["status"] in ("done", "failed"):
                print(f"[{elapsed:5.1f}s] 结束：{current['status']} 候选={current['match_count']}"
                      f" 错误={current.get('error')}")
                break
            if elapsed > 300:
                print(f"[{elapsed:5.1f}s] 超过 300 秒仍未结束，放弃观察")
                break

        candidates = call(base, f"/scrape/jobs/{job_id}/candidates")["data"]
        print(f"\n候选 {len(candidates)} 条：")
        for cand in candidates[:10]:
            print(f"  - [{cand['source']}] {cand['title']} (relevance={cand.get('relevance')})")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()
        print("\n=== 后端日志（含请求）===")
        text = log_path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "Request:" in line or "Response:" in line:
                continue
            if any(key in line for key in ("刮削", "Provider", "超时", "ERROR", "WARNING", "代理")):
                print("  " + line.strip()[:200])
        tmp.cleanup()


if __name__ == "__main__":
    main()
