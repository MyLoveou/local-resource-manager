"""Lazy local Chinese-CLIP ONNX runtime."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.ai.infrastructure.model_store import model_path, tokenizer_path

_MEAN = (0.48145466, 0.4578275, 0.40821073)
_STD = (0.26862954, 0.26130258, 0.27577711)
_MAX_TEXT_LENGTH = 52


class ClipRuntime:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session: Any = None
        self._tokenizer: Any = None
        self._numpy: Any = None

    def dependency_ready(self) -> bool:
        try:
            import numpy  # noqa: F401
            import onnxruntime  # noqa: F401
            import tokenizers  # noqa: F401
        except ImportError:
            return False
        return True

    def _load(self) -> None:
        if self._session is not None and self._tokenizer is not None:
            return
        if not model_path().is_file() or not tokenizer_path().is_file():
            raise RuntimeError("AI 模型尚未安装")
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(model_path()),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        tokenizer = Tokenizer.from_file(str(tokenizer_path()))
        tokenizer.enable_truncation(max_length=_MAX_TEXT_LENGTH)
        tokenizer.enable_padding(
            length=_MAX_TEXT_LENGTH,
            pad_id=0,
            pad_token="[PAD]",
        )
        self._tokenizer = tokenizer
        self._numpy = np

    def reload(self) -> None:
        with self._lock:
            self._session = None
            self._tokenizer = None
            self._numpy = None
            if self.dependency_ready() and model_path().is_file() and tokenizer_path().is_file():
                self._load()

    def _dummy_text(self) -> tuple[Any, Any]:
        np = self._numpy
        ids = np.array([[101, 102]], dtype=np.int64)
        return ids, np.ones_like(ids, dtype=np.int64)

    def _dummy_image(self) -> Any:
        np = self._numpy
        return np.zeros((1, 3, 224, 224), dtype=np.float32)

    @staticmethod
    def _normalize(vectors: Any) -> Any:
        np = __import__("numpy")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1e-12)

    def encode_text(self, texts: list[str]) -> Any:
        if not texts:
            return self._numpy.zeros((0, 512), dtype="float32")
        with self._lock:
            self._load()
            encodings = self._tokenizer.encode_batch(texts)
            ids = self._numpy.array([item.ids for item in encodings], dtype="int64")
            masks = self._numpy.array([item.attention_mask for item in encodings], dtype="int64")
            pixel_values = self._dummy_image()
            outputs = self._session.run(
                ["text_embeds"],
                {
                    "input_ids": ids,
                    "attention_mask": masks,
                    "pixel_values": pixel_values,
                },
            )
        return self._normalize(outputs[0].astype("float32"))

    def encode_images(self, paths: list[Path]) -> list[Any | None]:
        if not paths:
            return []
        from PIL import Image, ImageOps

        images: list[Image.Image] = []
        valid: list[int] = []
        for index, path in enumerate(paths):
            try:
                with Image.open(path) as opened:
                    image = ImageOps.exif_transpose(opened).convert("RGB")
                    images.append(image.resize((224, 224), Image.Resampling.BICUBIC))
                    valid.append(index)
            except Exception:
                continue
        if not images:
            return [None for _ in paths]
        with self._lock:
            self._load()
            np = self._numpy
            batch = np.stack(
                [
                    np.asarray(image, dtype="float32") / 255.0
                    for image in images
                ]
            )
            mean = np.array(_MEAN, dtype="float32")
            std = np.array(_STD, dtype="float32")
            batch = (batch - mean) / std
            batch = np.ascontiguousarray(batch.transpose(0, 3, 1, 2))
            ids, masks = self._dummy_text()
            outputs = self._session.run(
                ["image_embeds"],
                {
                    "pixel_values": batch,
                    "input_ids": ids,
                    "attention_mask": masks,
                },
            )
        vectors = self._normalize(outputs[0].astype("float32"))
        result: list[Any | None] = [None for _ in paths]
        for offset, index in enumerate(valid):
            result[index] = vectors[offset]
        return result


runtime = ClipRuntime()
