"""导入进度：按字节推进 + 速率与剩余时间。

按文件计数在复制大文件时会长时间不动（一个 8 GB 的 mkv 复制两分钟，进度条纹丝不动），
所以复制阶段每写一块就回报字节数，进度条按字节走。

放在单独模块还因为 `import_service.py` 已经贴着文件规模基线。
"""

from __future__ import annotations

import time
from collections import deque

CHUNK = 8 * 1024 * 1024
# 进度条分段：校验 0-30%，复制 30-90%，封面 90-100%
HASH_END = 30.0
COPY_END = 90.0


def advance(job) -> None:
    job.done += 1


def hash_message(plan_message: str, done: int, total: int) -> str:
    return f"{plan_message} · 校验 {done}/{total}"


def copy_message(plan_message: str, done: int, total: int, copied_gb: float) -> str:
    return f"{plan_message} · 复制 {done}/{total} · {copied_gb:.1f} GB"


def format_eta(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return ""
    minutes, rest = divmod(int(seconds), 60)
    if minutes <= 0:
        return f"剩余约 {rest} 秒"
    if minutes < 60:
        return f"剩余约 {minutes} 分 {rest} 秒"
    hours, minutes = divmod(minutes, 60)
    return f"剩余约 {hours} 小时 {minutes} 分"


class ProgressTracker:
    """把各阶段完成度折算成 0-100，并给出速率与 ETA。

    采样窗口取最近 10 秒，避免开头几个小文件把速率算得过于乐观。
    """

    def __init__(self, window_sec: float = 10.0) -> None:
        self._samples: deque[tuple[float, float]] = deque()
        self._window = window_sec
        self.speed_mbps: float | None = None
        self.eta_seconds: int | None = None

    def _sample(self, position: float) -> None:
        now = time.monotonic()
        self._samples.append((now, position))
        while self._samples and now - self._samples[0][0] > self._window:
            self._samples.popleft()

    def _rate(self) -> float:
        """每秒推进的百分比。"""
        if len(self._samples) < 2:
            return 0.0
        first_t, first_p = self._samples[0]
        last_t, last_p = self._samples[-1]
        elapsed = last_t - first_t
        if elapsed <= 0:
            return 0.0
        return max(0.0, (last_p - first_p) / elapsed)

    def hash_percent(self, done: int, total: int) -> float:
        position = (done / total) if total else 0.0
        return HASH_END * position

    def copy_percent(self, done: int, total: int) -> float:
        """按字节折算复制阶段进度，并更新速率与 ETA。"""
        position = (done / total) if total else 0.0
        percent = HASH_END + (COPY_END - HASH_END) * position
        self._sample(percent)
        rate = self._rate()
        if rate <= 0:
            return percent
        remaining = max(0.0, total - done)
        bytes_per_sec = rate / (COPY_END - HASH_END) * total
        if bytes_per_sec > 0:
            # 剩余不足 1 秒也报 1，避免进度条尾部 ETA 闪成空
            self.eta_seconds = max(1, int(remaining / bytes_per_sec))
            self.speed_mbps = bytes_per_sec / (1024 * 1024)
        return percent

    @staticmethod
    def cover_percent(done: int, total: int) -> float:
        position = (done / total) if total else 0.0
        return COPY_END + (100.0 - COPY_END) * position


_TRACKERS: dict[int, ProgressTracker] = {}


def tracker_for(job) -> ProgressTracker:
    """每个任务一个 tracker（按 id 缓存，任务结束即被 GC）。"""
    key = id(job)
    found = _TRACKERS.get(key)
    if found is None:
        found = ProgressTracker()
        _TRACKERS[key] = found
    return found


def copy_reporter(job, plan_message: str, index: int, total_files: int, base_bytes: int, bytes_total: int):
    """返回一个「收到已写字节」的回调，供分块复制使用。"""

    def report(written: int) -> None:
        done = base_bytes + written
        percent = tracker_for(job).copy_percent(done, bytes_total)
        job.percent = percent
        job.eta_seconds = tracker_for(job).eta_seconds
        job.speed_mbps = tracker_for(job).speed_mbps
        suffix = format_eta(float(job.eta_seconds)) if job.eta_seconds else ""
        job.message = (
            f"{plan_message} · 复制 {index + 1}/{total_files} · {done / 2**30:.1f} GB"
            + (f" · {suffix}" if suffix else "")
        )

    return report

def report_hash(job, plan_message: str, done: int, total: int) -> None:
    job.message = hash_message(plan_message, done, total)
    job.percent = tracker_for(job).hash_percent(done, total)
