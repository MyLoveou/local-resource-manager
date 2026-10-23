"""AI model status, indexing and semantic search."""

from __future__ import annotations

import asyncio
import base64
import json
import tempfile
from pathlib import Path

from sqlalchemy import case, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.jobs import Job, jobs
from app.ai.application.labels import LABELS, PROMPTS, select_labels
from app.ai.application.query import AttributeFilter, parse_query
from app.ai.application.schemas import (
    AIFusionResponse,
    AIJob,
    AIMatchExplanation,
    AIModelInfo,
    AIQueryInsight,
    AISearchResponse,
    AISimilarResponse,
    AIStatus,
)
from app.ai.infrastructure.model_store import (
    MODEL_DIM,
    MODEL_ID,
    MODEL_NAME,
    download_model,
    installed_size,
    is_installed,
)
from app.ai.infrastructure.caption_provider import caption_provider
from app.ai.infrastructure.image_hash import dhash_many, hamming
from app.ai.infrastructure.person_detector import person_detector
from app.ai.infrastructure.runtime import runtime
from app.library.domain.models import ResourceStatus, ResourceType
from app.library.infrastructure.orm import FileRow, ResourceRow
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.config import settings
from app.shared.db.db import get_session_factory

INDEX_BATCH_SIZE = 8


class AIServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


def job_schema(job: Job) -> AIJob:
    return AIJob(
        id=job.id,
        kind=job.kind,
        status=job.status,
        total=job.total,
        done=job.done,
        percent=job.percent,
        message=job.message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _model_info() -> AIModelInfo:
    return AIModelInfo(
        id=MODEL_ID,
        name=MODEL_NAME,
        installed=is_installed(),
        dim=MODEL_DIM,
        size_bytes=installed_size(),
    )


class AIService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def status(self) -> AIStatus:
        total = await self.session.scalar(
            select(func.count(distinct(ResourceRow.id)))
            .select_from(ResourceRow)
            .join(FileRow, FileRow.resource_id == ResourceRow.id)
            .where(
                ResourceRow.type == ResourceType.IMAGE.value,
                ResourceRow.status == ResourceStatus.ACTIVE.value,
                FileRow.role == "primary",
            )
        )
        indexed = await self.session.scalar(
            text("SELECT COUNT(*) FROM ai_vectors WHERE model_id = :model"),
            {"model": MODEL_ID},
        )
        updated = await self.session.scalar(
            text("SELECT MAX(updated_at) FROM ai_vectors WHERE model_id = :model"),
            {"model": MODEL_ID},
        )
        person_count_indexed = await self.session.scalar(
            text("SELECT COUNT(*) FROM ai_attributes WHERE feature = 'person_count'")
        )
        caption_indexed = await self.session.scalar(
            text("SELECT COUNT(*) FROM ai_documents")
        )
        ready = await caption_provider.available()
        vlm_runtime_ready = await caption_provider.runtime_available()
        vlm_models = await caption_provider.list_models() if vlm_runtime_ready else []
        return AIStatus(
            dependency_ready=runtime.dependency_ready(),
            model=_model_info(),
            indexed=int(indexed or 0),
            total=int(total or 0),
            person_count_indexed=int(person_count_indexed or 0),
            caption_ready=ready,
            caption_model=caption_provider.model if ready else "",
            caption_indexed=int(caption_indexed or 0),
            vlm_runtime_ready=vlm_runtime_ready,
            vlm_models=vlm_models,
            index_updated_at=str(updated) if updated else None,
        )

    async def get_job(self, job_id: str) -> AIJob:
        job = jobs.get(job_id)
        if job is None:
            raise AIServiceError("AI 任务不存在", 404)
        return job_schema(job)

    async def install_model(self) -> AIJob:
        if is_installed():
            raise AIServiceError("AI 模型已安装")
        if jobs.has_active():
            raise AIServiceError("已有 AI 任务在运行")
        job = jobs.create("install")
        jobs.start(job, self._run_install)
        return job_schema(job)

    async def _run_install(self, job: Job) -> None:
        def progress(done: int, total: int) -> None:
            jobs.update(job, total=total, done=done, message="正在下载模型")

        await download_model(progress)
        await asyncio.to_thread(runtime.reload)
        await asyncio.to_thread(person_detector.reload)
        jobs.update(job, done=job.total or job.done, message="模型安装完成")

    async def build_index(self) -> AIJob:
        if not is_installed():
            raise AIServiceError("请先安装 AI 模型")
        if not runtime.dependency_ready():
            raise AIServiceError("缺少 AI 运行依赖，请重新安装后端依赖")
        if jobs.has_active():
            raise AIServiceError("已有 AI 任务在运行")
        job = jobs.create("index")
        jobs.start(job, self._run_index)
        return job_schema(job)

    async def _collect_images(self) -> list[tuple[int, Path]]:
        stmt = (
            select(ResourceRow.id, FileRow.path, FileRow.role)
            .join(FileRow, FileRow.resource_id == ResourceRow.id)
            .where(
                ResourceRow.type == ResourceType.IMAGE.value,
                ResourceRow.status == ResourceStatus.ACTIVE.value,
                FileRow.role.in_(("primary", "thumbnail")),
            )
            .order_by(
                case((FileRow.role == "primary", 0), else_=1),
                ResourceRow.id,
            )
        )
        rows = (await self.session.execute(stmt)).all()
        chosen: dict[int, Path] = {}
        for resource_id, raw_path, _role in rows:
            if resource_id in chosen or not raw_path:
                continue
            path = Path(raw_path)
            if path.is_file():
                chosen[resource_id] = path
        return list(chosen.items())

    @staticmethod
    def _orientation(width: int, height: int) -> str:
        if width >= height * 1.05:
            return "landscape"
        if height >= width * 1.05:
            return "portrait"
        return "square"

    async def _save_attribute(
        self,
        session: AsyncSession,
        resource_id: int,
        feature: str,
        value: object,
        *,
        value_num: float | None = None,
        value_text: str | None = None,
        confidence: float | None = None,
        model: str | None = None,
    ) -> None:
        await session.execute(
            text(
                "INSERT INTO ai_attributes "
                "(resource_id, feature, value_json, value_num, value_text, confidence, model, updated_at) "
                "VALUES (:resource_id, :feature, :value_json, :value_num, :value_text, :confidence, :model, datetime('now')) "
                "ON CONFLICT(resource_id, feature) DO UPDATE SET "
                "value_json = excluded.value_json, value_num = excluded.value_num, "
                "value_text = excluded.value_text, confidence = excluded.confidence, "
                "model = excluded.model, updated_at = datetime('now')"
            ),
            {
                "resource_id": resource_id,
                "feature": feature,
                "value_json": json.dumps(value, ensure_ascii=False),
                "value_num": value_num,
                "value_text": value_text,
                "confidence": confidence,
                "model": model,
            },
        )

    async def _run_index(self, job: Job) -> None:
        factory = get_session_factory()
        async with factory() as session:
            service = AIService(session)
            images = await service._collect_images()
            jobs.update(job, total=len(images), done=0, message="准备图片")
            await session.execute(
                text("DELETE FROM ai_vectors WHERE model_id = :model"),
                {"model": MODEL_ID},
            )
            await session.execute(
                text(
                    "DELETE FROM ai_attributes "
                    "WHERE feature IN ('person_count', 'orientation', 'caption') "
                    "OR feature LIKE 'label:%'"
                )
            )
            await session.execute(text("DELETE FROM ai_hashes"))
            await session.commit()

            import numpy as np

            label_vectors = await asyncio.to_thread(
                runtime.encode_text, list(PROMPTS)
            )
            for offset in range(0, len(images), INDEX_BATCH_SIZE):
                batch = images[offset : offset + INDEX_BATCH_SIZE]
                paths = [path for _resource_id, path in batch]
                vectors = await asyncio.to_thread(runtime.encode_images, paths)
                detections = await asyncio.to_thread(person_detector.count_many, paths)
                hashes = await asyncio.to_thread(dhash_many, paths)
                for (resource_id, path), vector, detection, digest in zip(
                    batch, vectors, detections, hashes, strict=True
                ):
                    if digest is not None:
                        await session.execute(
                            text(
                                "INSERT INTO ai_hashes (resource_id, dhash, updated_at) "
                                "VALUES (:resource_id, :dhash, datetime('now')) "
                                "ON CONFLICT(resource_id) DO UPDATE SET "
                                "dhash = excluded.dhash, updated_at = datetime('now')"
                            ),
                            {"resource_id": resource_id, "dhash": digest},
                        )
                    if vector is not None:
                        await session.execute(
                            text(
                                "INSERT INTO ai_vectors "
                                "(resource_id, model_id, dim, vector, source_path, updated_at) "
                                "VALUES (:resource_id, :model, :dim, :vector, :path, datetime('now')) "
                                "ON CONFLICT(resource_id) DO UPDATE SET "
                                "model_id = excluded.model_id, dim = excluded.dim, "
                                "vector = excluded.vector, source_path = excluded.source_path, "
                                "updated_at = datetime('now')"
                            ),
                            {
                                "resource_id": resource_id,
                                "model": MODEL_ID,
                                "dim": int(vector.shape[0]),
                                "vector": vector.astype("<f4").tobytes(),
                                "path": str(path),
                            },
                        )
                    if vector is not None:
                        label_scores = label_vectors @ vector.astype("float32")
                        selected = select_labels([float(value) for value in label_scores])
                        for spec, score in selected:
                            await service._save_attribute(
                                session,
                                resource_id,
                                f"label:{spec.label}",
                                {"label": spec.label, "score": score},
                                value_num=score,
                                value_text=spec.label,
                                confidence=score,
                                model="clip-label",
                            )
                        caption = "?".join(spec.label for spec, _score in selected)
                        if caption:
                            await service._save_attribute(
                                session,
                                resource_id,
                                "caption",
                                {"text": caption},
                                value_text=caption,
                                confidence=1.0,
                                model="clip-label",
                            )
                    if detection is not None:
                        await service._save_attribute(
                            session,
                            resource_id,
                            "person_count",
                            detection.count,
                            value_num=detection.count,
                            confidence=detection.confidence,
                            model="yolov8n",
                        )
                        orientation = service._orientation(
                            detection.width, detection.height
                        )
                        await service._save_attribute(
                            session,
                            resource_id,
                            "orientation",
                            orientation,
                            value_text=orientation,
                            confidence=1.0,
                            model="image-dimensions",
                        )
                await session.commit()
                jobs.update(
                    job,
                    done=min(len(images), offset + len(batch)),
                    message=f"已索引 {min(len(images), offset + len(batch))}/{len(images)}",
                )

    async def _filter_resource_ids(
        self, filters: list[AttributeFilter]
    ) -> set[int] | None:
        if not filters:
            return None
        sets: list[set[int]] = []
        for item in filters:
            params: dict[str, object] = {"value": item.value}
            if item.feature == "person_count":
                condition = "feature = 'person_count'"
                if item.op == "eq":
                    condition += " AND value_num = :value"
                elif item.op == "gte":
                    condition += " AND value_num >= :value"
                elif item.op == "lte":
                    condition += " AND value_num <= :value"
                else:
                    continue
            elif item.feature == "orientation":
                condition = "feature = 'orientation' AND value_text = :value"
            else:
                continue
            rows = (
                await self.session.execute(
                    text(f"SELECT resource_id FROM ai_attributes WHERE {condition}"),
                    params,
                )
            ).scalars()
            sets.append(set(rows))
        if not sets:
            return None
        return set.intersection(*sets)

    async def _label_resource_ids(self, labels: list[str]) -> set[int] | None:
        if not labels:
            return None
        features = [f"label:{label}" for label in labels]
        placeholders = ", ".join(f":feature{index}" for index in range(len(features)))
        params = {f"feature{index}": feature for index, feature in enumerate(features)}
        rows = (
            await self.session.execute(
                text(
                    "SELECT DISTINCT resource_id FROM ai_attributes "
                    f"WHERE feature IN ({placeholders}) AND value_num >= 0.30"
                ),
                params,
            )
        ).scalars()
        return set(rows)

    async def pull_vlm(self, model: str) -> AIJob:
        model = model.strip()
        if not model:
            raise AIServiceError("模型名称不能为空")
        if not await caption_provider.runtime_available():
            raise AIServiceError("未检测到 Ollama，请先启动本地 VLM 服务")
        if jobs.has_active():
            raise AIServiceError("已有 AI 任务在运行")
        job = jobs.create("vlm-pull")
        jobs.start(job, lambda current: self._run_pull(current, model))
        return job_schema(job)

    async def _run_pull(self, job: Job, model: str) -> None:
        def progress(done: int, total: int, message: str) -> None:
            jobs.update(job, done=done, total=total, message=message)

        await caption_provider.pull(model, progress)
        jobs.update(job, done=job.total or job.done, message=f"模型 {model} 下载完成")

    async def analyze_images(self, resource_ids: list[int] | None = None) -> AIJob:
        if not await caption_provider.available():
            raise AIServiceError(
                f"尚未安装可用的 VLM 模型，请先运行：ollama pull {settings.vlm_model}"
            )
        if jobs.has_active():
            raise AIServiceError("已有 AI 任务在运行")
        job = jobs.create("caption")
        jobs.start(job, lambda current: self._run_analyze(current, resource_ids))
        return job_schema(job)

    async def _collect_analysis_images(
        self, resource_ids: list[int] | None
    ) -> list[tuple[int, Path]]:
        stmt = (
            select(ResourceRow.id, FileRow.path)
            .join(FileRow, FileRow.resource_id == ResourceRow.id)
            .where(
                ResourceRow.type == ResourceType.IMAGE.value,
                ResourceRow.status == ResourceStatus.ACTIVE.value,
                FileRow.role == "primary",
            )
            .order_by(ResourceRow.id)
        )
        if resource_ids:
            stmt = stmt.where(ResourceRow.id.in_(resource_ids))
        rows = (await self.session.execute(stmt)).all()
        chosen: dict[int, Path] = {}
        for resource_id, raw_path in rows:
            if resource_id in chosen or not raw_path:
                continue
            path = Path(raw_path)
            if path.is_file():
                chosen[resource_id] = path
        return list(chosen.items())

    async def _run_analyze(
        self, job: Job, resource_ids: list[int] | None
    ) -> None:
        factory = get_session_factory()
        async with factory() as session:
            service = AIService(session)
            images = await service._collect_analysis_images(resource_ids)
            jobs.update(job, total=len(images), done=0, message="准备分析文案")
            for index, (resource_id, path) in enumerate(images, start=1):
                document = await caption_provider.analyze(path)
                await session.execute(
                    text(
                        "INSERT INTO ai_documents "
                        "(resource_id, caption, short_caption, tags_json, attributes_json, ocr_text, "
                        "model_id, prompt_version, status, updated_at) "
                        "VALUES (:resource_id, :caption, :short_caption, :tags, :attributes, :ocr, "
                        ":model, :prompt_version, 'ready', datetime('now')) "
                        "ON CONFLICT(resource_id) DO UPDATE SET "
                        "caption = excluded.caption, short_caption = excluded.short_caption, "
                        "tags_json = excluded.tags_json, attributes_json = excluded.attributes_json, "
                        "ocr_text = excluded.ocr_text, model_id = excluded.model_id, "
                        "prompt_version = excluded.prompt_version, status = 'ready', "
                        "updated_at = datetime('now')"
                    ),
                    {
                        "resource_id": resource_id,
                        "caption": document.caption,
                        "short_caption": document.short_caption,
                        "tags": json.dumps(document.tags, ensure_ascii=False),
                        "attributes": json.dumps(document.attributes, ensure_ascii=False),
                        "ocr": document.ocr_text,
                        "model": document.model_id,
                        "prompt_version": document.prompt_version,
                    },
                )
                await session.execute(
                    text("DELETE FROM ai_tags WHERE resource_id = :id"),
                    {"id": resource_id},
                )
                for tag in document.tags:
                    await session.execute(
                        text(
                            "INSERT INTO ai_tags "
                            "(resource_id, tag, category, confidence, source, model_id) "
                            "VALUES (:resource_id, :tag, NULL, NULL, 'vlm', :model)"
                        ),
                        {"resource_id": resource_id, "tag": tag, "model": document.model_id},
                    )
                await session.commit()
                jobs.update(
                    job,
                    done=index,
                    message=f"已分析 {index}/{len(images)}",
                )

    async def _query_image_path(self, resource_id: int) -> Path | None:
        row = (
            await self.session.execute(
                select(FileRow.path)
                .where(
                    FileRow.resource_id == resource_id,
                    FileRow.role == "primary",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if not row:
            return None
        path = Path(row)
        return path if path.is_file() else None

    async def _query_vector(self, resource_id: int) -> list[float] | None:
        row = (
            await self.session.execute(
                text(
                    "SELECT vector FROM ai_vectors "
                    "WHERE resource_id = :resource_id AND model_id = :model"
                ),
                {"resource_id": resource_id, "model": MODEL_ID},
            )
        ).scalar_one_or_none()
        import numpy as np

        if row is not None:
            return np.frombuffer(bytes(row), dtype="<f4").astype("float32")
        path = await self._query_image_path(resource_id)
        if path is None:
            return None
        vectors = await asyncio.to_thread(runtime.encode_images, [path])
        if not vectors or vectors[0] is None:
            return None
        return vectors[0]

    async def _resource_meta(self, resource_ids: list[int]) -> dict[int, dict]:
        unique = sorted({int(item) for item in resource_ids if item is not None})
        result: dict[int, dict] = {
            resource_id: {
                "labels": [],
                "person_count": None,
                "orientation": None,
                "caption": "",
                "short_caption": "",
                "tags": [],
            }
            for resource_id in unique
        }
        if not unique:
            return result

        params = {f"id{index}": resource_id for index, resource_id in enumerate(unique)}
        placeholders = ", ".join(f":id{index}" for index in range(len(unique)))
        rows = (
            await self.session.execute(
                text(
                    "SELECT resource_id, feature, value_num, value_text, confidence "
                    f"FROM ai_attributes WHERE resource_id IN ({placeholders})"
                ),
                params,
            )
        ).all()
        labels_by_id: dict[int, list[tuple[float, str]]] = {
            resource_id: [] for resource_id in unique
        }
        for resource_id, feature, value_num, value_text, confidence in rows:
            meta = result[int(resource_id)]
            if feature == "person_count" and value_num is not None:
                meta["person_count"] = int(value_num)
            elif feature == "orientation":
                meta["orientation"] = value_text
            elif feature.startswith("label:") and value_text:
                labels_by_id[int(resource_id)].append(
                    (float(confidence or 0), str(value_text))
                )

        for resource_id, values in labels_by_id.items():
            values.sort(reverse=True)
            result[resource_id]["labels"] = [label for _score, label in values[:8]]

        docs = (
            await self.session.execute(
                text(
                    "SELECT resource_id, caption, short_caption, tags_json "
                    f"FROM ai_documents WHERE resource_id IN ({placeholders})"
                ),
                params,
            )
        ).all()
        for resource_id, caption, short_caption, raw_tags in docs:
            meta = result[int(resource_id)]
            meta["caption"] = str(caption or "")
            meta["short_caption"] = str(short_caption or "")
            try:
                tags = json.loads(raw_tags or "[]")
            except (TypeError, ValueError):
                tags = []
            if not isinstance(tags, list):
                tags = []
            meta["tags"] = [
                str(item).strip()
                for item in tags
                if isinstance(item, str) and str(item).strip()
            ][:12]
        return result

    @staticmethod
    def _orientation_label(value: str | None) -> str | None:
        return {
            "landscape": "横图",
            "portrait": "竖图",
            "square": "方图",
        }.get(value or "", value)

    def _text_query_insight(self, raw: str, parsed) -> AIQueryInsight:
        person_count = next(
            (
                int(item.value)
                for item in parsed.filters
                if item.feature == "person_count"
            ),
            None,
        )
        orientation = next(
            (
                str(item.value)
                for item in parsed.filters
                if item.feature == "orientation"
            ),
            None,
        )
        notes = []
        if parsed.labels:
            notes.append("标签条件来自固定 CLIP 词表，可能把相近场景误标为同一标签。")
        notes.append("相似度是 CLIP 文本向量与图片向量的余弦值；人数、方向、标签是硬过滤。")
        return AIQueryInsight(
            source="text",
            raw=raw,
            semantic_text=parsed.text,
            strategy="识别文字条件 → 人数/方向/标签硬过滤 → CLIP 相似度排序",
            labels=parsed.labels,
            filters=[item.label for item in parsed.filters],
            person_count=person_count,
            orientation=self._orientation_label(orientation),
            notes=notes,
        )

    def _image_query_insight(
        self,
        meta: dict | None,
        raw: str = "",
        *,
        extra_notes: list[str] | None = None,
    ) -> AIQueryInsight:
        meta = meta or {}
        notes = list(extra_notes or [])
        if not meta.get("caption"):
            notes.append("这张查询图还没有 VLM 文案；当前依据 CLIP 标签、人数和方向。")
        return AIQueryInsight(
            source="image",
            raw=raw,
            strategy="提取图片向量和 dHash → 近似重复优先 → CLIP 视觉相似度排序",
            caption=str(meta.get("caption") or ""),
            short_caption=str(meta.get("short_caption") or ""),
            tags=list(meta.get("tags") or []),
            labels=list(meta.get("labels") or []),
            person_count=(
                int(meta["person_count"])
                if meta.get("person_count") is not None
                else None
            ),
            orientation=self._orientation_label(meta.get("orientation")),
            notes=notes,
        )

    def _image_match_explanation(
        self,
        resource_id: int,
        meta: dict | None,
        *,
        semantic_score: float | None = None,
        duplicate_score: float | None = None,
        dhash_distance: int | None = None,
    ) -> AIMatchExplanation:
        meta = meta or {}
        reasons: list[str] = []
        if dhash_distance is not None:
            reasons.append(f"dHash 差异 {dhash_distance}/64，判定为近似重复")
        if semantic_score is not None:
            reasons.append(f"CLIP 视觉相似度 {semantic_score:.2f}")
        return AIMatchExplanation(
            resource_id=resource_id,
            reasons=reasons,
            semantic_score=semantic_score,
            duplicate_score=duplicate_score,
            dhash_distance=dhash_distance,
            caption=str(meta.get("caption") or ""),
            short_caption=str(meta.get("short_caption") or ""),
            tags=list(meta.get("tags") or []),
            person_count=(
                int(meta["person_count"])
                if meta.get("person_count") is not None
                else None
            ),
            orientation=self._orientation_label(meta.get("orientation")),
        )

    def _text_match_explanation(
        self,
        resource_id: int,
        meta: dict | None,
        parsed,
        semantic_score: float,
    ) -> AIMatchExplanation:
        meta = meta or {}
        reasons = [f"CLIP 语义相似度 {semantic_score:.2f}"]
        reasons.extend(item.label for item in parsed.filters)
        reasons.extend(f"标签命中：{label}" for label in parsed.labels)
        return AIMatchExplanation(
            resource_id=resource_id,
            reasons=reasons,
            semantic_score=semantic_score,
            caption=str(meta.get("caption") or ""),
            short_caption=str(meta.get("short_caption") or ""),
            tags=list(meta.get("tags") or []),
            matched_labels=list(parsed.labels),
            person_count=(
                int(meta["person_count"])
                if meta.get("person_count") is not None
                else None
            ),
            orientation=self._orientation_label(meta.get("orientation")),
        )

    async def _similar_from_query(
        self,
        query_vector,
        query_hash: str | None,
        mode: str,
        limit: int,
        source_id: int | None = None,
        query_insight: AIQueryInsight | None = None,
    ) -> AISimilarResponse:
        import numpy as np

        if mode not in {"auto", "semantic", "duplicate"}:
            raise AIServiceError("不支持的相似检索模式", 400)
        active_ids = set(
            (
                await self.session.execute(
                    select(ResourceRow.id).where(
                        ResourceRow.type == ResourceType.IMAGE.value,
                        ResourceRow.status == ResourceStatus.ACTIVE.value,
                    )
                )
            ).scalars()
        )
        if source_id is not None and source_id not in active_ids:
            raise AIServiceError("查询图片不存在", 404)

        rows = (
            await self.session.execute(
                text(
                    "SELECT resource_id, vector, dim FROM ai_vectors "
                    "WHERE model_id = :model"
                ),
                {"model": MODEL_ID},
            )
        ).all()
        all_ids = [row[0] for row in rows if row[0] in active_ids]
        ids = [item for item in all_ids if item != source_id]
        vector_by_id = {
            row[0]: np.frombuffer(bytes(row[1]), dtype="<f4").astype("float32")
            for row in rows
            if row[0] in active_ids and row[0] != source_id
        }
        indexed = len(all_ids)
        repo = ResourceRepository(self.session)
        duplicates: list[Resource] = []
        duplicate_scores: list[float] = []
        duplicate_distances: list[int] = []
        items: list[Resource] = []
        scores: list[float] = []

        if mode in {"auto", "duplicate"} and query_hash is not None:
            hash_rows = (
                await self.session.execute(
                    text("SELECT resource_id, dhash FROM ai_hashes")
                )
            ).all()
            matched = [
                (resource_id, hamming(query_hash, row_hash))
                for resource_id, row_hash in hash_rows
                if resource_id in active_ids
                and resource_id != source_id
                and row_hash
            ]
            matched.sort(key=lambda item: item[1])
            for candidate_id, distance in matched[:limit]:
                if distance > 10:
                    continue
                resource = await repo.get(candidate_id)
                if resource is None:
                    continue
                duplicates.append(resource)
                duplicate_scores.append(1.0 - distance / 64.0)
                duplicate_distances.append(distance)

        duplicate_ids = {item.id for item in duplicates}
        if mode in {"auto", "semantic"} and ids and query_vector is not None:
            matrix = np.stack([vector_by_id[item] for item in ids])
            raw_scores = matrix @ query_vector.astype("float32")
            order = np.argsort(-raw_scores)
            for index in order:
                if len(items) >= limit:
                    break
                candidate_id = ids[int(index)]
                if mode == "auto" and candidate_id in duplicate_ids:
                    continue
                resource = await repo.get(candidate_id)
                if resource is None:
                    continue
                items.append(resource)
                scores.append(float(raw_scores[int(index)]))

        if mode == "semantic" and query_vector is None:
            raise AIServiceError("查询图片尚未建立 AI 索引", 409)

        result_ids = [item.id for item in duplicates] + [item.id for item in items]
        meta_by_id = await self._resource_meta(
            [item for item in result_ids if item is not None]
        )
        duplicate_explanations = [
            self._image_match_explanation(
                item.id,
                meta_by_id.get(item.id),
                duplicate_score=duplicate_scores[index],
                dhash_distance=duplicate_distances[index],
            )
            for index, item in enumerate(duplicates)
            if item.id is not None
        ]
        explanations = [
            self._image_match_explanation(
                item.id,
                meta_by_id.get(item.id),
                semantic_score=scores[index],
            )
            for index, item in enumerate(items)
            if item.id is not None
        ]

        return AISimilarResponse(
            mode=mode,
            indexed=indexed,
            returned=len(items) + len(duplicates),
            items=items,
            scores=scores,
            duplicates=duplicates,
            duplicate_scores=duplicate_scores,
            query_insight=query_insight,
            explanations=explanations,
            duplicate_explanations=duplicate_explanations,
        )

    async def similar(
        self,
        resource_id: int,
        mode: str = "auto",
        limit: int = 30,
    ) -> AISimilarResponse:
        if not is_installed():
            raise AIServiceError("请先安装 AI 模型")
        if not runtime.dependency_ready():
            raise AIServiceError("缺少 AI 运行依赖，请重新安装后端依赖")
        if jobs.has_active_kind("index"):
            raise AIServiceError("AI 索引正在重建，请完成后再搜索", 409)

        query_vector = await self._query_vector(resource_id)
        query_hash = (
            await self.session.execute(
                text("SELECT dhash FROM ai_hashes WHERE resource_id = :id"),
                {"id": resource_id},
            )
        ).scalar_one_or_none()
        if query_hash is None:
            path = await self._query_image_path(resource_id)
            if path is not None:
                hashes = await asyncio.to_thread(dhash_many, [path])
                query_hash = hashes[0] if hashes else None
        query_meta = (await self._resource_meta([resource_id])).get(resource_id)
        return await self._similar_from_query(
            query_vector,
            query_hash,
            mode,
            limit,
            resource_id,
            self._image_query_insight(query_meta),
        )

    async def similar_file(
        self,
        data: bytes,
        filename: str = "",
        mode: str = "auto",
        limit: int = 30,
    ) -> AISimilarResponse:
        if not is_installed():
            raise AIServiceError("请先安装 AI 模型")
        if not runtime.dependency_ready():
            raise AIServiceError("缺少 AI 运行依赖，请重新安装后端依赖")
        if jobs.has_active_kind("index"):
            raise AIServiceError("AI 索引正在重建，请完成后再搜索", 409)
        if not data:
            raise AIServiceError("图片为空", 400)
        suffix = Path(filename).suffix.lower() or ".jpg"
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
            suffix = ".jpg"
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(data)
                temp_path = Path(handle.name)
            vectors = await asyncio.to_thread(runtime.encode_images, [temp_path])
            if not vectors or vectors[0] is None:
                raise AIServiceError("无法解析查询图片", 415)
            hashes = await asyncio.to_thread(dhash_many, [temp_path])
            detection = (
                await asyncio.to_thread(person_detector.count_many, [temp_path])
            )[0]
            labels: list[str] = []
            try:
                label_vectors = await asyncio.to_thread(
                    runtime.encode_text, list(PROMPTS)
                )
                selected = select_labels(
                    [float(value) for value in label_vectors @ vectors[0]]
                )
                labels = [spec.label for spec, _score in selected]
            except Exception:
                labels = []
            query_meta = {
                "labels": labels,
                "person_count": detection.count if detection is not None else None,
                "orientation": (
                    self._orientation(detection.width, detection.height)
                    if detection is not None
                    else None
                ),
            }
            return await self._similar_from_query(
                vectors[0],
                hashes[0] if hashes else None,
                mode,
                limit,
                None,
                self._image_query_insight(
                    query_meta,
                    filename,
                    extra_notes=[
                        "外部图片未生成 VLM 文案；当前依据 CLIP 标签、人数和方向。"
                    ],
                ),
            )
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    async def fusion(
        self,
        resource_id: int,
        query: str,
        limit: int = 30,
        strict: bool = False,
        image_weight: float = 0.5,
        text_weight: float = 0.5,
    ) -> AIFusionResponse:
        import numpy as np

        query = query.strip()
        if not query:
            raise AIServiceError("融合查询不能为空")
        if not is_installed():
            raise AIServiceError("尚未安装 AI 模型")
        if not runtime.dependency_ready():
            raise AIServiceError("当前环境缺少 AI 推理依赖")
        if jobs.has_active_kind("index"):
            raise AIServiceError("AI 索引正在重建，请稍后再试", 409)
        if image_weight < 0 or text_weight < 0 or image_weight + text_weight <= 0:
            raise AIServiceError("图文权重无效", 400)

        active_ids = set(
            (
                await self.session.execute(
                    select(ResourceRow.id).where(
                        ResourceRow.type == ResourceType.IMAGE.value,
                        ResourceRow.status == ResourceStatus.ACTIVE.value,
                    )
                )
            ).scalars()
        )
        if resource_id not in active_ids:
            raise AIServiceError("图片不存在", 404)
        source_vector = await self._query_vector(resource_id)
        if source_vector is None:
            raise AIServiceError("图片尚未建立 AI 向量，请先重建索引", 409)

        parsed = parse_query(query)
        text_vector = (await asyncio.to_thread(runtime.encode_text, [parsed.text]))[0]
        rows = (
            await self.session.execute(
                text(
                    "SELECT resource_id, vector, dim FROM ai_vectors "
                    "WHERE model_id = :model"
                ),
                {"model": MODEL_ID},
            )
        ).all()
        candidate_ids = await self._filter_resource_ids(parsed.filters)
        indexed = 0
        ids: list[int] = []
        vectors = []
        for row_id, raw_vector, dim in rows:
            if row_id not in active_ids or int(dim) != len(text_vector):
                continue
            vector = np.frombuffer(bytes(raw_vector), dtype="<f4").astype("float32")
            if vector.shape[0] != int(dim):
                continue
            indexed += 1
            if row_id == resource_id:
                continue
            if candidate_ids is not None and row_id not in candidate_ids:
                continue
            ids.append(row_id)
            vectors.append(vector)
        if not ids:
            return AIFusionResponse(
                mode="fusion",
                indexed=indexed,
                matched=0,
                returned=0,
                items=[],
                scores=[],
                filters=[item.label for item in parsed.filters],
            )

        matrix = np.stack(vectors)
        image_scores = matrix @ source_vector.astype("float32")
        text_scores = matrix @ text_vector.astype("float32")
        image_order = np.argsort(-image_scores)
        text_order = np.argsort(-text_scores)
        pool = max(100, min(len(ids), max(limit * 5, 100)))
        allowed: set[int] | None = None
        if strict:
            allowed = set(ids[int(index)] for index in image_order[:pool])
            allowed &= set(ids[int(index)] for index in text_order[:pool])

        total_weight = image_weight + text_weight
        image_rank = {int(index): rank + 1 for rank, index in enumerate(image_order)}
        text_rank = {int(index): rank + 1 for rank, index in enumerate(text_order)}
        fused: list[tuple[int, float]] = []
        for index, candidate_id in enumerate(ids):
            if allowed is not None and candidate_id not in allowed:
                continue
            score = (
                image_weight / (60 + image_rank[index]) / total_weight
                + text_weight / (60 + text_rank[index]) / total_weight
            )
            fused.append((index, score))
        fused.sort(key=lambda item: item[1], reverse=True)
        matched = len(fused)
        repo = ResourceRepository(self.session)
        items: list[Resource] = []
        scores: list[float] = []
        for index, score in fused[: max(1, min(limit, 100))]:
            resource = await repo.get(ids[index])
            if resource is None:
                continue
            items.append(resource)
            scores.append(round(float(score), 6))
        return AIFusionResponse(
            mode="fusion",
            indexed=indexed,
            matched=matched,
            returned=len(items),
            items=items,
            scores=scores,
            filters=[item.label for item in parsed.filters],
        )

    async def search(self, query: str, limit: int = 30) -> AISearchResponse:
        query = query.strip()
        if not query:
            return AISearchResponse(items=[], scores=[], indexed=0, matched=0, returned=0)
        if not is_installed():
            raise AIServiceError("请先安装 AI 模型")
        if not runtime.dependency_ready():
            raise AIServiceError("缺少 AI 运行依赖，请重新安装后端依赖")
        if jobs.has_active_kind("index"):
            raise AIServiceError("AI 索引正在重建，请完成后再搜索", 409)

        import numpy as np

        parsed = parse_query(query)
        query_insight = self._text_query_insight(query, parsed)
        text_vector = (await asyncio.to_thread(runtime.encode_text, [parsed.text]))[0]
        rows = (
            await self.session.execute(
                text(
                    "SELECT resource_id, vector, dim FROM ai_vectors "
                    "WHERE model_id = :model"
                ),
                {"model": MODEL_ID},
            )
        ).all()
        active_ids = set(
            (
                await self.session.execute(
                    select(ResourceRow.id).where(
                        ResourceRow.type == ResourceType.IMAGE.value,
                        ResourceRow.status == ResourceStatus.ACTIVE.value,
                    )
                )
            ).scalars()
        )
        candidate_ids = await self._filter_resource_ids(parsed.filters)
        label_ids = await self._label_resource_ids(parsed.labels)
        if label_ids is not None:
            candidate_ids = (
                label_ids if candidate_ids is None else candidate_ids & label_ids
            )
        all_ids: list[int] = []
        filtered_ids: list[int] = []
        vectors = []
        for resource_id, raw_vector, dim in rows:
            if resource_id not in active_ids or int(dim) != len(text_vector):
                continue
            vector = np.frombuffer(bytes(raw_vector), dtype="<f4").astype("float32")
            if vector.shape[0] != int(dim):
                continue
            all_ids.append(resource_id)
            if candidate_ids is not None and resource_id not in candidate_ids:
                continue
            filtered_ids.append(resource_id)
            vectors.append(vector)
        if not vectors:
            return AISearchResponse(
                items=[],
                scores=[],
                indexed=len(all_ids),
                matched=0,
                returned=0,
                filters=[item.label for item in parsed.filters]
                + [f"标签={label}" for label in parsed.labels],
                query_insight=query_insight,
            )

        matrix = np.stack(vectors)
        scores = matrix @ text_vector.astype("float32")
        order = np.argsort(-scores)[: max(1, min(limit, 100))]
        repo = ResourceRepository(self.session)
        items = []
        result_scores: list[float] = []
        result_ids: list[int] = []
        for index in order:
            resource_id = filtered_ids[int(index)]
            resource = await repo.get(resource_id)
            if resource is None:
                continue
            items.append(resource)
            result_scores.append(float(scores[int(index)]))
            result_ids.append(resource_id)
        meta_by_id = await self._resource_meta(result_ids)
        explanations = [
            self._text_match_explanation(
                resource_id,
                meta_by_id.get(resource_id),
                parsed,
                result_scores[index],
            )
            for index, resource_id in enumerate(result_ids)
        ]
        return AISearchResponse(
            items=items,
            scores=result_scores,
            indexed=len(all_ids),
            matched=len(filtered_ids),
            returned=len(items),
            filters=[item.label for item in parsed.filters]
            + [f"标签={label}" for label in parsed.labels],
            query_insight=query_insight,
            explanations=explanations,
        )
