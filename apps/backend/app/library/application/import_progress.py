"""导入进度文案：把计划说明和实时进度拼成一行。

放在单独模块是因为 `import_service.py` 已经贴着文件规模基线，
再加几行拼字符串就会超。
"""

from __future__ import annotations


def advance(job) -> None:
    job.done += 1


def hash_message(plan_message: str, done: int, total: int) -> str:
    return f"{plan_message} · 校验 {done}/{total}"


def copy_message(plan_message: str, done: int, total: int, copied_gb: float) -> str:
    return f"{plan_message} · 复制 {done}/{total} · {copied_gb:.1f} GB"


def advance_copy(job, plan_message: str, done: int, total: int, copied_gb: float) -> None:
    job.done += 1
    job.message = copy_message(plan_message, done, total, copied_gb)