"""YOLOv8n person detector used as a structured image attribute."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from app.ai.infrastructure.model_store import person_model_path

_INPUT_SIZE = 640
_CONFIDENCE = 0.3
_NMS_IOU = 0.45
_MIN_AREA = 900
_PERSON_CLASS = 0


@dataclass(frozen=True)
class PersonDetection:
    count: int
    width: int
    height: int
    confidence: float


def _iou(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


class PersonDetector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session = None
        self._numpy = None

    def available(self) -> bool:
        return person_model_path().is_file() and person_model_path().stat().st_size > 0

    def _load(self) -> None:
        if self._session is not None:
            return
        if not self.available():
            raise RuntimeError("人数检测模型尚未安装")
        import numpy as np
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(person_model_path()),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self._numpy = np

    def reload(self) -> None:
        with self._lock:
            self._session = None
            self._numpy = None

    def count_many(self, paths: list[Path]) -> list[PersonDetection | None]:
        if not paths:
            return []
        if not self.available():
            return [None for _ in paths]
        from PIL import Image, ImageOps

        result: list[PersonDetection | None] = []
        with self._lock:
            self._load()
            np = self._numpy
            for path in paths:
                try:
                    with Image.open(path) as opened:
                        image = ImageOps.exif_transpose(opened).convert("RGB")
                        width, height = image.size
                        scale = min(_INPUT_SIZE / width, _INPUT_SIZE / height)
                        new_width = max(1, round(width * scale))
                        new_height = max(1, round(height * scale))
                        resized = image.resize(
                            (new_width, new_height),
                            Image.Resampling.BILINEAR,
                        )
                        canvas = Image.new("RGB", (_INPUT_SIZE, _INPUT_SIZE), (114, 114, 114))
                        pad_x = (_INPUT_SIZE - new_width) // 2
                        pad_y = (_INPUT_SIZE - new_height) // 2
                        canvas.paste(resized, (pad_x, pad_y))
                        tensor = np.asarray(canvas, dtype="float32") / 255.0
                        tensor = np.ascontiguousarray(tensor.transpose(2, 0, 1)[None])
                        output = self._session.run(None, {"images": tensor})[0][0].T
                    scores = output[:, 4 + _PERSON_CLASS]
                    keep = scores >= _CONFIDENCE
                    boxes = output[keep, :4]
                    scores = scores[keep]
                    boxes[:, 0] -= boxes[:, 2] / 2
                    boxes[:, 1] -= boxes[:, 3] / 2
                    boxes[:, 2] += boxes[:, 0]
                    boxes[:, 3] += boxes[:, 1]
                    order = np.argsort(-scores)
                    boxes = boxes[order]
                    scores = scores[order]
                    selected_boxes: list[list[float]] = []
                    selected_scores: list[float] = []
                    for box, score in zip(boxes, scores, strict=True):
                        values = [float(value) for value in box]
                        if (values[2] - values[0]) * (values[3] - values[1]) < _MIN_AREA:
                            continue
                        if any(_iou(values, other) > _NMS_IOU for other in selected_boxes):
                            continue
                        selected_boxes.append(values)
                        selected_scores.append(float(score))
                    result.append(
                        PersonDetection(
                            count=len(selected_boxes),
                            width=width,
                            height=height,
                            confidence=round(
                                sum(selected_scores) / len(selected_scores), 3
                            ) if selected_scores else 0.0,
                        )
                    )
                except Exception:
                    result.append(None)
        return result


person_detector = PersonDetector()
