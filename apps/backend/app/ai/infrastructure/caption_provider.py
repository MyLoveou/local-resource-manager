"""Optional local VLM caption/tag provider (Ollama).

The model is deliberately not bundled. The desktop app keeps working with
CLIP/YOLO when Ollama is absent.
"""

from __future__ import annotations

import asyncio
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

PROMPT_VERSION = "caption-v4"
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
  "ocr": ["图中清晰可读的文字，最多5条，不要重复"],
  "tags": ["3到8个中文标签"]
}
""".strip()


def _prompt_with_context(context: dict | None) -> str:
    if not context:
        return PROMPT
    labels = (
        ("categories", "分类"),
        ("tags", "已有标签"),
        ("characters", "角色"),
        ("persons", "扮演者"),
    )
    lines: list[str] = []
    for key, label in labels:
        values = [str(value).strip() for value in context.get(key, []) if str(value).strip()]
        if values:
            lines.append(f"{label}：{'、'.join(values[:12])}")
    if not lines:
        return PROMPT
    return (
        f"{PROMPT}\n\n"
        "以下是用户已整理的人工信息，仅作参考，不要机械重复，不要编造不存在的关系：\n"
        + "\n".join(lines)
    )


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
    if start < 0:
        raise ValueError("VLM 未返回有效 JSON")
    end = cleaned.rfind("}")
    payload = cleaned[start : end + 1] if end > start else cleaned[start:]
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        # A VLM may hit the output limit in the middle of a long OCR list.
        # Recover fields that were already complete instead of dropping an
        # otherwise usable caption.
        def field(name: str) -> str:
            match = re.search(
                rf'"{name}"\s*:\s*"((?:\\.|[^"\\])*)"', cleaned, re.S
            )
            return str(match.group(1)).strip() if match else ""

        caption = field("caption")
        short_caption = field("short_caption")
        tag_block = re.search(r'"tags"\s*:\s*\[(.*?)(?:\]|$)', cleaned, re.S)
        tags = (
            re.findall(r'"((?:\\.|[^"\\])*)"', tag_block.group(1))
            if tag_block
            else []
        )
        if caption or short_caption or tags:
            return {
                "caption": caption,
                "short_caption": short_caption,
                "tags": tags,
            }
        raise exc
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

    @property
    def provider(self) -> str:
        return (settings.vlm_provider or "ollama").strip().lower()

    @property
    def _is_openai(self) -> bool:
        return self.provider in {"openai", "openai-compatible", "lmstudio", "llamacpp"}

    @property
    def _base_url(self) -> str:
        if self._is_openai:
            return (settings.vlm_base_url or "http://127.0.0.1:1234/v1").rstrip("/")
        return settings.vlm_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        if settings.vlm_api_key:
            return {"Authorization": f"Bearer {settings.vlm_api_key}"}
        return {}

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=3.0, headers=self._headers()) as client:
                if self._is_openai:
                    response = await client.get(f"{self._base_url}/models")
                    response.raise_for_status()
                    return [
                        str(item.get("id", ""))
                        for item in response.json().get("data", [])
                        if item.get("id")
                    ]
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                return [
                    str(item.get("name", ""))
                    for item in response.json().get("models", [])
                    if item.get("name")
                ]
        except Exception:
            return []

    async def list_model_details(self) -> list[dict]:
        if self._is_openai:
            names = await self.list_models()
            return [
                {
                    "name": name,
                    "size_bytes": 0,
                    "capabilities": ["vision"] if self._looks_like_vision(name) else [],
                    "supports_vision": self._looks_like_vision(name),
                    "selected": name == self.model,
                }
                for name in names
            ]
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])

                async def describe(item: dict) -> dict:
                    name = str(item.get("name") or "")
                    show: dict = {}
                    if name:
                        try:
                            detail = await client.post(
                                f"{settings.vlm_url.rstrip('/')}/api/show",
                                json={"name": name},
                            )
                            detail.raise_for_status()
                            show = detail.json()
                        except Exception:
                            show = {}
                    capabilities = show.get("capabilities") or item.get("capabilities") or []
                    caps = [str(value) for value in capabilities]
                    model_info = show.get("model_info") or {}
                    family = str(
                        (show.get("details") or {}).get("family")
                        or (item.get("details") or {}).get("family")
                        or ""
                    )
                    supports_vision = (
                        "vision" in caps
                        or any("vision" in str(key).lower() for key in model_info)
                        or "vl" in family.lower()
                    )
                    return {
                        "name": name,
                        "size_bytes": int(item.get("size") or 0),
                        "capabilities": caps,
                        "supports_vision": supports_vision,
                        "selected": name == self.model,
                    }

                return await asyncio.gather(*(describe(item) for item in models))
        except Exception:
            return []

    @staticmethod
    def _looks_like_vision(name: str) -> bool:
        value = name.lower()
        return any(
            marker in value
            for marker in ("vl", "vision", "llava", "minicpm", "moondream")
        )

    async def select_model(self, model: str) -> dict:
        details = await self.list_model_details()
        matched = next((item for item in details if item["name"] == model), None)
        if matched is None:
            raise ValueError("??????")
        if not matched["supports_vision"]:
            raise ValueError("??????????")
        self.model = model
        self._ready = None
        return matched

    async def runtime_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0, headers=self._headers()) as client:
                url = (
                    f"{self._base_url}/models"
                    if self._is_openai
                    else f"{self._base_url}/api/tags"
                )
                response = await client.get(url)
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
        if self._is_openai:
            raise RuntimeError("OpenAI-compatible ?????????????????")
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

    def _post_body(self, image_base64: str, prompt: str) -> dict:
        return {
            "model": self.model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 512},
        }

    def _openai_body(self, image_base64: str, prompt: str) -> dict:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                        },
                    ],
                }
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }

    async def analyze(self, path: Path, context: dict | None = None) -> CaptionDocument:
        prompt = _prompt_with_context(context)
        if not await self.available():
            raise RuntimeError(
                f"未找到可用的 VLM 模型，请先运行：ollama pull {settings.vlm_model}"
            )

        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image.thumbnail((768, 768), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=86)
        image_base64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        value: dict | None = None
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    timeout=settings.vlm_timeout, headers=self._headers()
                ) as client:
                    if self._is_openai:
                        response = await client.post(
                            f"{self._base_url}/chat/completions",
                            json=self._openai_body(image_base64, prompt),
                        )
                        response.raise_for_status()
                        payload = response.json()
                        choices = payload.get("choices") or []
                        raw = (
                            str(choices[0].get("message", {}).get("content", ""))
                            if choices
                            else ""
                        )
                    else:
                        response = await client.post(
                            f"{self._base_url}/api/generate",
                            json=self._post_body(image_base64, prompt),
                        )
                        response.raise_for_status()
                        payload = response.json()
                        raw = str(payload.get("response", ""))
                value = _parse_json(raw)
                break
            except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                last_error = exc
                response = getattr(exc, "response", None)
                body = str(getattr(response, "text", "") or "")
                if "token repeat limit" in body.lower():
                    # The same sampling request will repeat again; let the
                    # service switch to the optional anime tagger immediately.
                    raise
                status = getattr(response, "status_code", None)
                retryable = isinstance(exc, ValueError) or status is None or status >= 500
                if attempt == 0 and retryable:
                    await asyncio.sleep(1.5)
                    continue
                raise
        if value is None:
            raise RuntimeError(f"VLM ?????{last_error}")
        tags: list[str] = []
        for item in _string_list(value.get("tags")):
            if item not in tags:
                tags.append(item)
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
