"""Optional local VLM caption/tag provider (Ollama).

The model is deliberately not bundled. The desktop app keeps working with
CLIP/YOLO when Ollama is absent.
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageOps

from app.shared.config import settings

PROMPT_VERSION = "caption-v2"
PROMPT = """
请分析这张图片，只返回一个 JSON 对象，不要 markdown，不要解释。
描述主体、人物、场景、动作、颜色、物体、服饰；无法判断的字段用 null。
JSON 格式：
{
  "caption": "一句话中文描述",
  "short_caption": "不超过15字的短标题",
  "scene": ["室内/室外/海边/街道等"],
  "actions": ["站立/坐着/跑步/拍照等"],
  "colors": ["画面主要颜色"],
  "objects": [{"name": "物体", "color": "颜色", "confidence": 0.0}],
  "clothing": ["服饰"],
  "people_count": 0,
  "ocr": ["图中清晰可读的文字"],
  "tags": ["3到8个中文标签"]
}
""".strip()


@dataclass
class CaptionDocument:
    caption: str
    short_caption: str
    tags: list[str] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)
    ocr_text: str = ""
    model_id: str = ""
    prompt_version: str = PROMPT_VERSION


def _parse_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?\s*|```\s*", "", raw).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("VLM 未返回有效 JSON")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("VLM JSON 不是对象")
    return value


def _string_list(value: object, limit: int = 16) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    ][:limit]


class CaptionProvider:
    def __init__(self) -> None:
        self.model = settings.vlm_model
        self._ready: bool | None = None
        self._checked_at = 0.0

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{settings.vlm_url.rstrip('/')}/api/tags")
                response.raise_for_status()
                return [
                    str(item.get("name", ""))
                    for item in response.json().get("models", [])
                    if item.get("name")
                ]
        except Exception:
            return []

    async def runtime_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{settings.vlm_url.rstrip('/')}/api/tags")
                response.raise_for_status()
                return True
        except Exception:
            return False

    async def available(self) -> bool:
        now = time.monotonic()
        if self._ready is not None and now - self._checked_at < 10:
            return self._ready
        try:
            names = await self.list_models()
            self._ready = any(
                name == self.model
                or name.split(":", 1)[0] == self.model.split(":", 1)[0]
                for name in names
            )
        except Exception:
            self._ready = False
        self._checked_at = now
        return self._ready

    async def pull(self, model: str, progress) -> None:
        if not await self.runtime_available():
            raise RuntimeError(
                f"未检测到 Ollama，请先启动本地服务：{settings.vlm_url}"
            )
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=None)
        ) as client:
            async with client.stream(
                "POST",
                f"{settings.vlm_url.rstrip('/')}/api/pull",
                json={"name": model, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    total = int(data.get("total") or 0)
                    completed = int(data.get("completed") or 0)
                    progress(completed, total, str(data.get("status") or "下载中"))
        self._ready = None
        self.model = model

    def _post_body(self, image_base64: str) -> dict:
        return {
            "model": self.model,
            "prompt": PROMPT,
            "images": [image_base64],
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192},
        }

    async def analyze(self, path: Path) -> CaptionDocument:
        if not await self.available():
            raise RuntimeError(
                f"尚未安装可用的 VLM 模型，请先运行：ollama pull {settings.vlm_model}"
            )
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image.thumbnail((768, 768), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=86)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        async with httpx.AsyncClient(timeout=settings.vlm_timeout) as client:
            response = await client.post(
                f"{settings.vlm_url.rstrip('/')}/api/generate",
                json=self._post_body(image_base64),
            )
            response.raise_for_status()
            payload = response.json()
        value = _parse_json(str(payload.get("response", "")))
        tags = _string_list(value.get("tags"))
        for key in ("scene", "actions", "colors", "clothing"):
            for item in _string_list(value.get(key)):
                if item not in tags:
                    tags.append(item)
        objects = value.get("objects")
        attributes = {
            "scene": _string_list(value.get("scene")),
            "actions": _string_list(value.get("actions")),
            "colors": _string_list(value.get("colors")),
            "clothing": _string_list(value.get("clothing")),
            "objects": objects if isinstance(objects, list) else [],
            "people_count": value.get("people_count"),
        }
        return CaptionDocument(
            caption=str(value.get("caption") or "").strip(),
            short_caption=str(value.get("short_caption") or "").strip(),
            tags=tags[:16],
            attributes=attributes,
            ocr_text="\n".join(_string_list(value.get("ocr"))),
            model_id=self.model,
        )


caption_provider = CaptionProvider()
