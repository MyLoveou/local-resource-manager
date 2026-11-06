"""导入进度：分段百分比、速率/ETA、分块复制的回调。"""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.library.application.import_progress import (
    COPY_END,
    HASH_END,
    ProgressTracker,
    copy_reporter,
    format_eta,
    report_hash,
)
from app.shared.fs.file_ops import FileOps


class TrackerTests(unittest.TestCase):
    def test_hash_segment_scales_to_30(self) -> None:
        tracker = ProgressTracker()
        self.assertEqual(tracker.hash_percent(0, 10), 0.0)
        self.assertEqual(tracker.hash_percent(10, 10), HASH_END)

    def test_copy_segment_starts_after_hash(self) -> None:
        tracker = ProgressTracker()
        self.assertEqual(tracker.copy_percent(0, 100), HASH_END)
        self.assertEqual(tracker.copy_percent(100, 100), COPY_END)

    def test_copy_percent_is_monotonic(self) -> None:
        tracker = ProgressTracker()
        values = [tracker.copy_percent(done, 1000) for done in range(0, 1001, 100)]
        self.assertEqual(values, sorted(values))

    def test_eta_appears_after_samples(self) -> None:
        tracker = ProgressTracker(window_sec=60)
        tracker.copy_percent(0, 1000)
        time.sleep(0.05)
        tracker.copy_percent(100, 1000)
        time.sleep(0.05)
        tracker.copy_percent(200, 1000)
        self.assertIsNotNone(tracker.eta_seconds)
        self.assertGreater(tracker.eta_seconds or 0, 0)
        self.assertIsNotNone(tracker.speed_mbps)

    def test_zero_total_does_not_divide(self) -> None:
        tracker = ProgressTracker()
        self.assertEqual(tracker.hash_percent(0, 0), 0.0)
        self.assertEqual(tracker.copy_percent(0, 0), HASH_END)


class FormatTests(unittest.TestCase):
    def test_seconds(self) -> None:
        self.assertEqual(format_eta(45), "剩余约 45 秒")

    def test_minutes(self) -> None:
        self.assertEqual(format_eta(150), "剩余约 2 分 30 秒")

    def test_hours(self) -> None:
        self.assertEqual(format_eta(3700), "剩余约 1 小时 1 分")

    def test_none_or_zero_is_empty(self) -> None:
        self.assertEqual(format_eta(None), "")
        self.assertEqual(format_eta(0), "")


class ReportTests(unittest.TestCase):
    def test_report_hash_sets_percent(self) -> None:
        job = SimpleNamespace(message="", percent=0.0)
        report_hash(job, "计划", 5, 10)
        self.assertIn("校验 5/10", job.message)
        self.assertAlmostEqual(job.percent, HASH_END / 2)

    def test_copy_reporter_updates_job(self) -> None:
        job = SimpleNamespace(message="", percent=0.0, eta_seconds=None, speed_mbps=None)
        report = copy_reporter(job, "计划", 0, 2, 0, 1000)
        report(500)
        self.assertGreater(job.percent, HASH_END)
        self.assertIn("复制 1/2", job.message)


class CopyProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_chunks_are_reported_and_content_matches(self) -> None:
        src = self.root / "src.bin"
        payload = b"x" * (3 * (8 << 20) + 123)
        src.write_bytes(payload)
        dest = self.root / "out" / "dest.bin"
        seen: list[int] = []

        FileOps().copy_with_progress(src, dest, seen.append, chunk=8 << 20)

        self.assertEqual(dest.read_bytes(), payload)
        self.assertEqual(seen, sorted(seen))
        self.assertEqual(seen[-1], len(payload))

    def test_zero_byte_file_still_copies(self) -> None:
        src = self.root / "empty.bin"
        src.write_bytes(b"")
        dest = self.root / "dest.bin"
        seen: list[int] = []
        FileOps().copy_with_progress(src, dest, seen.append)
        self.assertTrue(dest.exists())
        self.assertEqual(seen, [])
