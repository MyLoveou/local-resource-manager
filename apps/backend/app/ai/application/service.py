"""AI model status, indexing and semantic search."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import case, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.jobs import Job, jobs
from app.ai.application.labels import LABELS, PROMPTS, select_labels
from app.ai.application.query import AttributeFilter, parse_query
from app.ai.application.schemas import AIJob, AIModelInfo, AISearchResponse, AISimilarResponse, AIStatus
from app.ai.infrastructure.model_store import (
    MODEL_DIM,
    MODEL_ID,
    MODEL_NAME,
    download_model,
    installed_size,
    is_installed,
)
from app.ai.infrastructure.image_hash import dhash_many, hamming
from app.ai.infrastructure.person_detector import person_detector
from app.ai.infrastructure.runtime import runtime
from app.library.domain.models import ResourceStatus, ResourceType
from app.library.infrastructure.orm import FileRow, ResourceRow
from app.library.infrastructure.repositories import ResourceRepository
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
        return AIStatus(
            dependency_ready=runtime.dependency_ready(),
            model=_model_info(),
            indexed=int(indexed or 0),
            total=int(total or 0),
            person_count_indexed=int(person_count_indexed or 0),
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

    async def similar(
        self,
        resource_id: int,
        mode: str = "auto",
        limit: int = 30,
    ) -> AISimilarResponse:
        import numpy as np

        if mode not in {"auto", "semantic", "duplicate"}:
            raise AIServiceError("不支持的相似检索模式", 400)
        if not is_installed():
            raise AIServiceError("请先安装 AI 模型")
        if not runtime.dependency_ready():
            raise AIServiceError("缺少 AI 运行依赖，请重新安装后端依赖")
        if jobs.has_active_kind("index"):
            raise AIServiceError("AI 索引正在重建，请完成后再搜索", 409)

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
        ids = [
            row[0]
            for row in rows
            if row[0] in active_ids and row[0] != resource_id
        ]
        vector_by_id = {
            row[0]: np.frombuffer(bytes(row[1]), dtype="<f4").astype("float32")
            for row in rows
            if row[0] in active_ids and row[0] != resource_id
        }
        indexed = len(vector_by_id) + (1 if resource_id in {row[0] for row in rows} else 0)
        repo = ResourceRepository(self.session)
        duplicates: list[Resource] = []
        duplicate_scores: list[float] = []
        items: list[Resource] = []
        scores: list[float] = []

        if mode in {"auto", "duplicate"}:
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
            if query_hash is not None:
                hash_rows = (
                    await self.session.execute(
                        text("SELECT resource_id, dhash FROM ai_hashes")
                    )
                ).all()
                matched = [
                    (resource_id_, hamming(query_hash, row_hash))
                    for resource_id_, row_hash in hash_rows
                    if resource_id_ in active_ids
                    and resource_id_ != resource_id
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

        duplicate_ids = {item.id for item in duplicates}
        if mode in {"auto", "semantic"} and ids:
            query_vector = await self._query_vector(resource_id)
            if query_vector is None:
                if mode == "semantic":
                    raise AIServiceError("查询图片尚未建立 AI 索引", 409)
            else:
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

        return AISimilarResponse(
            mode=mode,
            indexed=indexed,
            returned=len(items) + len(duplicates),
            items=items,
            scores=scores,
            duplicates=duplicates,
            duplicate_scores=duplicate_scores,
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
            )

        matrix = np.stack(vectors)
        scores = matrix @ text_vector.astype("float32")
        order = np.argsort(-scores)[: max(1, min(limit, 100))]
        repo = ResourceRepository(self.session)
        items = []
        result_scores: list[float] = []
        for index in order:
            resource_id = filtered_ids[int(index)]
            resource = await repo.get(resource_id)
            if resource is None:
                continue
            items.append(resource)
            result_scores.append(float(scores[int(index)]))
        return AISearchResponse(
            items=items,
            scores=result_scores,
            indexed=len(all_ids),
            matched=len(filtered_ids),
            returned=len(items),
            filters=[item.label for item in parsed.filters]
            + [f"标签={label}" for label in parsed.labels],
        )
