"""刮削队列的接线检查。

上一版提交里 `_worker_loop` 调用了不存在的 `_open_task`，直到用户点刮削才报
`name '_open_task' is not defined`。函数级单测不会碰 worker，所以这里用一层
廉价但有效的契约测试兜住：模块里该有的符号必须真的存在且可调用。
"""

from __future__ import annotations

import inspect
import unittest

from app.scrape.application import queue as scrape_queue


class QueueContractTests(unittest.TestCase):
    def test_task_helpers_exist(self) -> None:
        for name in ("_open_task", "_close_task"):
            self.assertTrue(hasattr(scrape_queue, name), f"缺少 {name}")
            self.assertTrue(inspect.iscoroutinefunction(getattr(scrape_queue, name)))

    def test_worker_references_defined_symbols(self) -> None:
        source = inspect.getsource(scrape_queue._worker_loop)
        for name in ("_open_task", "_close_task", "run_search", "JOB_TIMEOUT_SEC"):
            self.assertIn(name, source)

    def test_timeout_is_bounded(self) -> None:
        self.assertGreaterEqual(scrape_queue.JOB_TIMEOUT_SEC, 0)
        self.assertLessEqual(scrape_queue.JOB_TIMEOUT_SEC, 300)
