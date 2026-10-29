"""音轨枚举与 remux：用假 ffprobe/ffmpeg 验证解析与缓存。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.library.application.audio_tracks import (
    ensure_remuxed,
    list_audio_tracks,
)

FFPROBE_JSON = {
    "streams": [
        {"index": 1, "codec_name": "flac", "channels": 2, "tags": {"language": "jpn", "title": "日语"}},
        {"index": 2, "codec_name": "aac", "channels": 6, "tags": {"language": "chi"}},
        {"index": 3, "codec_name": "opus", "channels": 2},
    ]
}


class ListTracksTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.video = Path(tmp.name) / "v.mkv"
        self.video.write_bytes(b"x")

    def _run(self, payload: dict, returncode: int = 0):
        stdout = json.dumps(payload).encode()

        def fake_run(*_args, **_kwargs):
            return type("R", (), {"returncode": returncode, "stdout": stdout, "stderr": b""})()

        return fake_run

    def test_parses_all_audio_streams(self) -> None:
        with patch("app.library.application.audio_tracks.shutil.which", return_value="ffprobe"), patch(
            "app.library.application.audio_tracks.subprocess.run",
            side_effect=self._run(FFPROBE_JSON),
        ):
            tracks = list_audio_tracks(self.video)
        self.assertEqual([t["index"] for t in tracks], [0, 1, 2])
        self.assertEqual(tracks[0]["language"], "jpn")
        self.assertIn("日语", tracks[0]["label"])
        self.assertEqual(tracks[1]["channels"], 6)
        self.assertIn("中文", tracks[1]["label"])
        self.assertEqual(tracks[2]["codec"], "opus")

    def test_no_ffprobe_returns_empty(self) -> None:
        with patch("app.library.application.audio_tracks.shutil.which", return_value=None):
            self.assertEqual(list_audio_tracks(self.video), [])

    def test_nonzero_exit_returns_empty(self) -> None:
        with patch("app.library.application.audio_tracks.shutil.which", return_value="ffprobe"), patch(
            "app.library.application.audio_tracks.subprocess.run",
            side_effect=self._run({}, returncode=1),
        ):
            self.assertEqual(list_audio_tracks(self.video), [])

    def test_missing_file_returns_empty(self) -> None:
        with patch("app.library.application.audio_tracks.shutil.which", return_value="ffprobe"):
            self.assertEqual(list_audio_tracks(self.video.parent / "nope.mkv"), [])


class RemuxTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.source = self.base / "v.mkv"
        self.source.write_bytes(b"x")

    def test_creates_cache_file(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command, **_kwargs):
            calls.append(command)
            Path(command[-1]).write_bytes(b"remuxed")
            return type("R", (), {"returncode": 0, "stderr": b""})()

        with patch("app.library.application.audio_tracks.shutil.which", return_value="ffmpeg"), patch(
            "app.library.application.audio_tracks.subprocess.run", side_effect=fake_run
        ):
            target = ensure_remuxed(self.source, 1, self.base)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertTrue(target.exists())
        self.assertIn("-map", calls[0])
        self.assertIn("0:a:1", calls[0])

    def test_reuses_cache_on_second_call(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command, **_kwargs):
            calls.append(command)
            Path(command[-1]).write_bytes(b"remuxed")
            return type("R", (), {"returncode": 0, "stderr": b""})()

        with patch("app.library.application.audio_tracks.shutil.which", return_value="ffmpeg"), patch(
            "app.library.application.audio_tracks.subprocess.run", side_effect=fake_run
        ):
            first = ensure_remuxed(self.source, 0, self.base)
            second = ensure_remuxed(self.source, 0, self.base)
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)

    def test_failure_returns_none(self) -> None:
        def fake_run(command, **_kwargs):
            return type("R", (), {"returncode": 1, "stderr": b"boom"})()

        with patch("app.library.application.audio_tracks.shutil.which", return_value="ffmpeg"), patch(
            "app.library.application.audio_tracks.subprocess.run", side_effect=fake_run
        ):
            self.assertIsNone(ensure_remuxed(self.source, 0, self.base))
