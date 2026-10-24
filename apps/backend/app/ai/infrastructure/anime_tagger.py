"""Optional WD14 anime tagger used as a fallback for VLM caption failures."""

from __future__ import annotations

import csv
import threading
from pathlib import Path

import httpx
from PIL import Image, ImageOps

from app.ai.infrastructure.caption_provider import CaptionDocument
from app.shared.config import settings

MODEL_ID = "wd14-moat-tagger-v2"
MODEL_FILE = "model.onnx"
TAGS_FILE = "selected_tags.csv"
MODEL_BYTES = 326_197_340
TAGS_BYTES = 253_906
MODEL_URL = (
    "https://huggingface.co/SmilingWolf/wd-v1-4-moat-tagger-v2/"
    "resolve/main/model.onnx"
)
TAGS_URL = (
    "https://huggingface.co/SmilingWolf/wd-v1-4-moat-tagger-v2/"
    "resolve/main/selected_tags.csv"
)
THRESHOLD = 0.35
TAG_ZH = {
    "1girl": "1???",
    "1boy": "1???",
    "2girls": "2???",
    "2boys": "2???",
    "solo": "??",
    "multiple_girls": "????",
    "long_hair": "??",
    "short_hair": "??",
    "blue_hair": "??",
    "red_hair": "??",
    "pink_hair": "??",
    "blonde_hair": "??",
    "white_hair": "??",
    "black_hair": "??",
    "purple_hair": "??",
    "blue_eyes": "??",
    "red_eyes": "??",
    "purple_eyes": "??",
    "closed_eyes": "??",
    "open_mouth": "??",
    "smile": "??",
    "looking_at_viewer": "????",
    "flower": "?",
    "flowers": "?",
    "dress": "???",
    "shirt": "??",
    "school_uniform": "??",
    "cosplay": "????",
    "indoors": "??",
    "outdoors": "??",
    "lying": "??",
    "on_back": "??",
    "sitting": "??",
    "standing": "??",
    "solo_focus": "????",
    "upper_body": "???",
    "portrait": "??",
    "cleavage": "??",
    "breasts": "??",
    "detached_sleeves": "?????",
    "hair_over_one_eye": "???????",
    "no_shoes": "??",
    "black_background": "????",
    "simple_background": "????",
    "monochrome": "??",
    "greyscale": "??",
    "comic": "??",
}


def model_dir() -> Path:
    return settings.db_path.parent / "models" / MODEL_ID


def model_path() -> Path:
    return model_dir() / MODEL_FILE


def tags_path() -> Path:
    return model_dir() / TAGS_FILE


def is_installed() -> bool:
    return model_path().is_file() and tags_path().is_file()


def installed_size() -> int:
    return sum(path.stat().st_size for path in (model_path(), tags_path()) if path.is_file())


async def download(progress) -> None:
    model_dir().mkdir(parents=True, exist_ok=True)
    total = MODEL_BYTES + TAGS_BYTES
    done = 0
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, read=180.0),
        headers={"User-Agent": "local-resource-manager/0.2"},
    ) as client:
        for url, target in ((MODEL_URL, model_path()), (TAGS_URL, tags_path())):
            if target.is_file() and target.stat().st_size > 0:
                done += target.stat().st_size
                progress(done, total)
                continue
            part = target.with_suffix(target.suffix + ".part")
            part.unlink(missing_ok=True)
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with part.open("wb") as handle:
                        async for chunk in response.aiter_bytes(1024 * 256):
                            handle.write(chunk)
                            done += len(chunk)
                            progress(done, total)
                part.replace(target)
            except Exception:
                part.unlink(missing_ok=True)
                raise


class AnimeTagger:
    def __init__(self) -> None:
        self._session = None
        self._tags: list[dict[str, str]] | None = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        return is_installed()

    def _load(self) -> None:
        if self._session is not None and self._tags is not None:
            return
        import onnxruntime as ort

        if not is_installed():
            raise RuntimeError("动漫标签模型尚未安装")
        with tags_path().open(encoding="utf-8", newline="") as handle:
            self._tags = list(csv.DictReader(handle))
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(model_path()),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

    def analyze(self, path: Path) -> CaptionDocument:
        with self._lock:
            self._load()
            with Image.open(path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB").resize(
                    (448, 448), Image.Resampling.BICUBIC
                )
            import numpy as np

            values = np.asarray(image, dtype=np.float32)
            scores = self._session.run(
                None, {"input_1:0": values[None]}
            )[0][0]
            rows = self._tags or []
            selected = []
            for index in np.argsort(-scores):
                score = float(scores[index])
                if score < THRESHOLD:
                    break
                if index >= len(rows):
                    continue
                row = rows[int(index)]
                if str(row.get("category")) == "9":
                    continue
                name = str(row.get("name") or "").strip()
                if name:
                    selected.append(name)
                if len(selected) >= 12:
                    break
            tags = list(dict.fromkeys(selected))
            if not tags:
                raise RuntimeError("动漫标签模型没有返回有效标签")
            caption = "动漫插画，" + "，".join(tags[:8])
            return CaptionDocument(
                caption=caption,
                short_caption="，".join(tags[:3]),
                tags=tags,
                attributes={"tags": tags, "anime_tagger": MODEL_ID},
                model_id=MODEL_ID,
                prompt_version="wd14-v1",
            )


anime_tagger = AnimeTagger()
