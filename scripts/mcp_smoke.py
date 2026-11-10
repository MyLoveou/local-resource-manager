"""冒烟测试 gitmove 的 MCP 服务：initialize + tools/list。"""

from __future__ import annotations

import json
import subprocess
import sys
import time

EXE = r"D:\Project\GitMove\gitmove-v2\target\release\gitmove-core.exe"
WORKSPACE = r"D:\Project\资源管理器"


def send(proc, payload: dict) -> None:
    line = json.dumps(payload, ensure_ascii=False)
    proc.stdin.write(line + "\n")
    proc.stdin.flush()


def read_reply(proc, want_id: int, timeout: float = 20.0) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("id") == want_id:
            return payload
    return None


def main() -> int:
    proc = subprocess.Popen(
        [EXE, "-C", WORKSPACE, "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    try:
        send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "dsh-smoke", "version": "0"},
            },
        })
        init = read_reply(proc, 1)
        if init is None:
            print("initialize 无响应")
            print(proc.stderr.read()[:500])
            return 1
        info = init.get("result", {}).get("serverInfo", {})
        print(f"initialize OK: {info}")

        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listed = read_reply(proc, 2)
        if listed is None:
            print("tools/list 无响应")
            return 1
        tools = listed.get("result", {}).get("tools", [])
        print(f"tools = {len(tools)}")
        for tool in tools:
            print("  -", tool.get("name"))
        return 0
    finally:
        proc.kill()


if __name__ == "__main__":
    sys.exit(main())
