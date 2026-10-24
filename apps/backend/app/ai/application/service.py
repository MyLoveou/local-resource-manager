"""AI model status, indexing and semantic search."""

from __future__ import annotations

import asyncio
import base64
import json
import random
import tempfile
from datetime import UTC, datetime

import httpx
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
    AIDeviceInfo,
    AIPerformance,
    AIPerformancePatch,
    AIQueryInsight,
    AISearchResponse,
    AISimilarResponse,
    AIStatus,
    AIVLMModelInfo,
    AIVLMRuntime,
)
from app.ai.infrastructure import ollama_runtime
from app.ai.infrastructure import anime_tagger
from app.ai.infrastructure import device_info as device_hints
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
from app.shared.log import logger, operations_logger

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
        failed=job.failed,
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
        stored_model = await self.session.scalar(
            text("SELECT value FROM ai_preferences WHERE key = 'vlm_model'")
        )
        if stored_model:
            caption_provider.model = str(stored_model)
        vlm_runtime_ready = await caption_provider.runtime_available()
        details = (
            await caption_provider.list_model_details() if vlm_runtime_ready else []
        )
        ready = await caption_provider.available()
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
            vlm_provider=caption_provider.provider,
            anime_tagger_ready=anime_tagger.is_installed(),
            anime_tagger_size=anime_tagger.installed_size(),
            vlm_models=[str(item["name"]) for item in details],
            vlm_model_details=[
                AIVLMModelInfo(
                    name=str(item["name"]),
                    size_bytes=int(item.get("size_bytes") or 0),
                    capabilities=list(item.get("capabilities") or []),
                    supports_vision=bool(item.get("supports_vision")),
                    selected=bool(item.get("selected")),
                )
                for item in details
            ],
            index_updated_at=str(updated) if updated else None,
        )

    async def list_jobs(self, limit: int = 20) -> list[AIJob]:
        rows = (
            await self.session.execute(
                text(
                    "SELECT id, kind, status, total, done, failed, message, "
                    "created_at, updated_at FROM ai_jobs "
                    "ORDER BY created_at DESC LIMIT :limit"
                ),
                {"limit": max(1, min(limit, 100))},
            )
        ).all()
        return [
            AIJob(
                id=row[0],
                kind=row[1],
                status=row[2],
                total=int(row[3] or 0),
                done=int(row[4] or 0),
                failed=int(row[5] or 0),
                percent=(
                    max(0, min(100, round(int(row[4] or 0) * 100 / int(row[3]))))
                    if int(row[3] or 0) > 0
                    else None
                ),
                message=str(row[6] or ""),
                created_at=str(row[7]),
                updated_at=str(row[8]),
            )
            for row in rows
        ]

    async def suggestions(self, limit: int = 30, offset: int = 0) -> list:
        rows = (
            await self.session.execute(
                text(
                    "SELECT d.resource_id, r.title, d.caption, d.short_caption, "
                    "d.tags_json FROM ai_documents d "
                    "JOIN resources r ON r.id = d.resource_id "
                    "WHERE r.status = 'active' ORDER BY d.resource_id"
                )
            )
        ).all()
        tag_rows = (
            await self.session.execute(
                text(
                    "SELECT ai.resource_id, ai.tag "
                    "FROM ai_tags ai JOIN resources r ON r.id = ai.resource_id "
                    "WHERE ai.source IN ('vlm', 'wd14') AND r.status = 'active' "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM resource_tags rt "
                    "JOIN tags t ON t.id = rt.tag_id "
                    "WHERE rt.resource_id = ai.resource_id AND t.name = ai.tag"
                    ") ORDER BY ai.resource_id, ai.tag"
                )
            )
        ).all()
        tags_by_resource: dict[int, list[str]] = {}
        for resource_id, tag in tag_rows:
            values = tags_by_resource.setdefault(int(resource_id), [])
            if tag and tag not in values:
                values.append(str(tag))

        media_rows = (
            await self.session.execute(
                text(
                    "SELECT f.resource_id, f.id, f.role FROM files f "
                    "JOIN resources r ON r.id = f.resource_id "
                    "WHERE r.status = 'active' AND f.role IN ('thumbnail', 'primary') "
                    "ORDER BY CASE WHEN f.role = 'thumbnail' THEN 0 ELSE 1 END, f.id"
                )
            )
        ).all()
        thumbnails: dict[int, str] = {}
        for resource_id, file_id, role in media_rows:
            rid = int(resource_id)
            if rid in thumbnails:
                continue
            if role == "thumbnail":
                thumbnails[rid] = f"/library/resources/{rid}/files/{int(file_id)}/content"
            else:
                thumbnails[rid] = f"/library/resources/{rid}/content"

        character_rows = (
            await self.session.execute(
                text("SELECT id, name FROM characters ORDER BY id")
            )
        ).all()
        character_aliases: dict[int, list[str]] = {}
        for character_id, alias in (
            await self.session.execute(
                text("SELECT character_id, alias FROM character_aliases")
            )
        ).all():
            character_aliases.setdefault(int(character_id), []).append(str(alias))
        person_rows = (
            await self.session.execute(text("SELECT id, name FROM persons ORDER BY id"))
        ).all()
        person_aliases: dict[int, list[str]] = {}
        for person_id, alias in (
            await self.session.execute(
                text("SELECT person_id, alias FROM person_aliases")
            )
        ).all():
            person_aliases.setdefault(int(person_id), []).append(str(alias))
        collection_rows = (
            await self.session.execute(
                text("SELECT id, title, description FROM collections ORDER BY id")
            )
        ).all()

        existing_characters = set(
            (
                await self.session.execute(
                    text("SELECT resource_id, character_id FROM resource_characters")
                )
            ).all()
        )
        existing_persons = set(
            (
                await self.session.execute(
                    text("SELECT resource_id, person_id FROM resource_persons")
                )
            ).all()
        )
        existing_collections = set(
            (
                await self.session.execute(
                    text("SELECT resource_id, collection_id FROM collection_items")
                )
            ).all()
        )

        grouped: dict[int, dict] = {}
        for resource_id, title, caption, short_caption, tags_json in rows:
            rid = int(resource_id)
            text_blob = " ".join(
                str(value or "") for value in (caption, short_caption, tags_json)
            ).lower()
            item = grouped.setdefault(
                rid,
                {
                    "resource_id": rid,
                    "title": str(title),
                    "thumbnail_path": thumbnails.get(rid),
                    "tags": tags_by_resource.get(rid, [])[:12],
                    "characters": [],
                    "persons": [],
                    "collections": [],
                },
            )
            for character_id, name in character_rows:
                names = [str(name), *character_aliases.get(int(character_id), [])]
                if (rid, int(character_id)) in existing_characters:
                    continue
                if any(len(value.strip()) >= 2 and value.strip().lower() in text_blob for value in names):
                    if len(item["characters"]) < 3:
                        item["characters"].append(
                            {"id": int(character_id), "name": str(name)}
                        )
            for person_id, name in person_rows:
                names = [str(name), *person_aliases.get(int(person_id), [])]
                if (rid, int(person_id)) in existing_persons:
                    continue
                if any(len(value.strip()) >= 2 and value.strip().lower() in text_blob for value in names):
                    if len(item["persons"]) < 3:
                        item["persons"].append({"id": int(person_id), "name": str(name)})
            for collection_id, collection_title, description in collection_rows:
                if (rid, int(collection_id)) in existing_collections:
                    continue
                names = [str(collection_title)]
                if description:
                    names.append(str(description))
                if any(len(value.strip()) >= 2 and value.strip().lower() in text_blob for value in names):
                    if len(item["collections"]) < 3:
                        item["collections"].append(
                            {"id": int(collection_id), "name": str(collection_title)}
                        )

        result = [
            item
            for item in grouped.values()
            if item["tags"] or item["characters"] or item["persons"] or item["collections"]
        ]
        size = max(1, min(limit, 100))
        start = max(0, offset)
        return result[start : start + size]

    async def vlm_runtime_status(self) -> AIVLMRuntime:
        preferred = await self.session.scalar(
            text("SELECT value FROM ai_preferences WHERE key = 'ollama_bin'")
        )
        data = await ollama_runtime.runtime_status(str(preferred or ""))
        return AIVLMRuntime(**data)

    async def select_ollama_binary(self, path: str) -> AIVLMRuntime:
        raw = path.strip()
        operations_logger.info("ai.ollama.select path=%s", raw)
        candidate = Path(raw).expanduser()
        if not raw or not candidate.is_file():
            raise AIServiceError("??? Ollama ???????? ollama.exe", 400)
        await self.session.execute(
            text(
                "INSERT INTO ai_preferences (key, value, updated_at) "
                "VALUES ('ollama_bin', :value, datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET "
                "value = excluded.value, updated_at = datetime('now')"
            ),
            {"value": str(candidate.resolve())},
        )
        await self.session.commit()
        return await self.vlm_runtime_status()

    async def start_ollama_runtime(self) -> AIVLMRuntime:
        operations_logger.info("ai.ollama.start")
        preferred = await self.session.scalar(
            text("SELECT value FROM ai_preferences WHERE key = 'ollama_bin'")
        )
        binary = ollama_runtime.detect_binary(str(preferred or ""))
        if not binary:
            raise AIServiceError("???? Ollama???????? ollama.exe", 400)
        try:
            data = await ollama_runtime.start_runtime(binary)
        except Exception as exc:
            raise AIServiceError(str(exc) or "Ollama ????", 400) from exc
        return AIVLMRuntime(**data)

    async def clear_jobs(self) -> None:
        if jobs.has_active():
            raise AIServiceError("有 AI 任务运行时不能清空历史")
        await self.session.execute(text("DELETE FROM ai_jobs"))
        await self.session.commit()
        operations_logger.info("ai.jobs.clear")

    async def performance(self) -> AIPerformance:
        info = device_hints.device_info()
        recommended = device_hints.recommendation(info)
        stored_mode = await self.session.scalar(
            text("SELECT value FROM ai_preferences WHERE key = 'ai_concurrency_mode'")
        )
        stored_manual = await self.session.scalar(
            text("SELECT value FROM ai_preferences WHERE key = 'ai_concurrency'")
        )
        mode = str(stored_mode or "balanced").strip().lower()
        if mode not in {"safe", "balanced", "max", "manual"}:
            mode = "balanced"
        try:
            manual = max(1, min(4, int(stored_manual or recommended["balanced"])))
        except (TypeError, ValueError):
            manual = recommended["balanced"]
        effective = manual if mode == "manual" else recommended.get(mode, 1)
        return AIPerformance(
            device=AIDeviceInfo(**info),
            mode=mode,
            manual=manual,
            effective=max(1, min(4, int(effective))),
            **recommended,
        )

    async def update_performance(self, patch: AIPerformancePatch) -> AIPerformance:
        values: dict[str, str] = {}
        if patch.mode is not None:
            mode = patch.mode.strip().lower()
            if mode not in {"safe", "balanced", "max", "manual"}:
                raise AIServiceError("无效的 AI 并发模式", 400)
            values["ai_concurrency_mode"] = mode
        if patch.manual is not None:
            values["ai_concurrency"] = str(max(1, min(4, int(patch.manual))))
        for key, value in values.items():
            await self.session.execute(
                text(
                    "INSERT INTO ai_preferences (key, value, updated_at) "
                    "VALUES (:key, :value, datetime('now')) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                    "updated_at = datetime('now')"
                ),
                {"key": key, "value": value},
            )
        await self.session.commit()
        return await self.performance()

    async def effective_concurrency(self) -> int:
        performance = await self.performance()
        return performance.effective

    async def select_vlm(self, model: str) -> AIStatus:
        model = model.strip()
        operations_logger.info("ai.vlm.select model=%s", model)
        if not model:
            raise AIServiceError("模型名称不能为空")
        try:
            await caption_provider.select_model(model)
        except ValueError as exc:
            raise AIServiceError(str(exc), 400) from exc
        await self.session.execute(
            text(
                "INSERT INTO ai_preferences (key, value, updated_at) "
                "VALUES ('vlm_model', :value, datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET "
                "value = excluded.value, updated_at = datetime('now')"
            ),
            {"value": model},
        )
        await self.session.commit()
        return await self.status()

    async def get_job(self, job_id: str) -> AIJob:
        job = jobs.get(job_id)
        if job is None:
            raise AIServiceError("AI 任务不存在", 404)
        return job_schema(job)


    async def install_model(self) -> AIJob:
        operations_logger.info("ai.model.install requested")
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

    async def build_index(self, full: bool = False) -> AIJob:
        operations_logger.info("ai.index.requested full=%s", full)
        if not is_installed():
            raise AIServiceError("请先安装 AI 模型")
        if not runtime.dependency_ready():
            raise AIServiceError("缺少 AI 运行依赖，请重新安装后端依赖")
        if jobs.has_active():
            raise AIServiceError("已有 AI 任务在运行")
        job = jobs.create("index")
        jobs.start(job, lambda current: self._run_index(current, full))
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

    async def _indexed_ids(self) -> set[int]:
        rows = (
            await self.session.execute(
                text("SELECT resource_id FROM ai_vectors WHERE model_id = :model"),
                {"model": MODEL_ID},
            )
        ).scalars()
        return set(rows)

    async def _run_index(self, job: Job, full: bool = False) -> None:
        factory = get_session_factory()
        async with factory() as session:
            service = AIService(session)
            all_images = await service._collect_images()
            indexed = set() if full else await service._indexed_ids()
            images = [
                (resource_id, path)
                for resource_id, path in all_images
                if resource_id not in indexed
            ]
            jobs.update(
                job,
                total=len(images),
                done=0,
                message="准备建立索引" if full else "准备增量索引",
            )
            if full:
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

            label_vectors = await asyncio.to_thread(
                runtime.encode_text, list(PROMPTS)
            )
            processed: set[int] = set()
            await service._index_image_batches(
                session, job, images, label_vectors, processed
            )

            # Resources can be imported while an index run is active. Catch
            # them up before reporting completion, so a follow-up import does
            # not require the user to remember to index again.
            for _ in range(2):
                refreshed = await service._collect_images()
                indexed_now = set() if full else await service._indexed_ids()
                missing = [
                    (resource_id, path)
                    for resource_id, path in refreshed
                    if resource_id not in processed and resource_id not in indexed_now
                ]
                if not missing:
                    break
                jobs.update(
                    job,
                    total=len(processed) + len(missing),
                    message=f"发现 {len(missing)} 张新增图片，继续补索引",
                )
                await service._index_image_batches(
                    session, job, missing, label_vectors, processed
                )

            final_indexed = set() if full else await service._indexed_ids()
            remaining = [
                (resource_id, path)
                for resource_id, path in await service._collect_images()
                if resource_id not in processed and resource_id not in final_indexed
            ]
            if remaining:
                jobs.update(
                    job,
                    message=f"索引完成，仍有 {len(remaining)} 张新增图片待索引",
                )
            else:
                jobs.update(job, message=f"索引完成，共 {len(processed)} 张")

    async def _index_image_batches(
        self,
        session: AsyncSession,
        job: Job,
        images: list[tuple[int, Path]],
        label_vectors,
        processed: set[int],
    ) -> None:
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
                        await self._save_attribute(
                            session,
                            resource_id,
                            f"label:{spec.label}",
                            {"label": spec.label, "score": score},
                            value_num=score,
                            value_text=spec.label,
                            confidence=score,
                            model="clip-label",
                        )
                    caption = "、".join(spec.label for spec, _score in selected)
                    if caption:
                        await self._save_attribute(
                            session,
                            resource_id,
                            "caption",
                            {"text": caption},
                            value_text=caption,
                            confidence=1.0,
                            model="clip-label",
                        )
                if detection is not None:
                    await self._save_attribute(
                        session,
                        resource_id,
                        "person_count",
                        detection.count,
                        value_num=detection.count,
                        confidence=detection.confidence,
                        model="yolov8n",
                    )
                    orientation = self._orientation(
                        detection.width, detection.height
                    )
                    await self._save_attribute(
                        session,
                        resource_id,
                        "orientation",
                        orientation,
                        value_text=orientation,
                        confidence=1.0,
                        model="image-dimensions",
                    )
                processed.add(resource_id)
            await session.commit()
            jobs.update(
                job,
                done=len(processed),
                message=f"已索引 {len(processed)}/{job.total}",
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

    async def install_anime_tagger(self) -> AIJob:
        operations_logger.info("ai.anime_tagger.install requested")
        if anime_tagger.is_installed():
            raise AIServiceError("?????????")
        if jobs.has_active():
            raise AIServiceError("?? AI ?????")
        job = jobs.create("anime-install")
        jobs.start(job, self._run_anime_install)
        return job_schema(job)

    async def _run_anime_install(self, job: Job) -> None:
        def progress(done: int, total: int) -> None:
            jobs.update(job, total=total, done=done, message="????????")

        await anime_tagger.download(progress)
        jobs.update(job, done=job.total or job.done, message="??????????")

    async def pull_vlm(self, model: str) -> AIJob:
        operations_logger.info("ai.vlm.pull model=%s", model)
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
        async with get_session_factory()() as session:
            await session.execute(
                text(
                    "INSERT INTO ai_preferences (key, value, updated_at) "
                    "VALUES ('vlm_model', :value, datetime('now')) "
                    "ON CONFLICT(key) DO UPDATE SET "
                    "value = excluded.value, updated_at = datetime('now')"
                ),
                {"value": model},
            )
            await session.commit()
        jobs.update(job, done=job.total or job.done, message=f"模型 {model} 下载完成")

    async def analyze_images(
        self,
        resource_ids: list[int] | None = None,
        only_pending: bool = True,
    ) -> AIJob:
        if not await caption_provider.available():
            raise AIServiceError(
                f"尚未安装可用的 VLM 模型，请先运行：ollama pull {caption_provider.model}"
            )
        if jobs.has_active():
            raise AIServiceError("已有 AI 任务在运行")
        operations_logger.info(
            "ai.caption.requested resource_ids=%s only_pending=%s",
            resource_ids,
            only_pending,
        )
        job = jobs.create("caption")
        jobs.start(
            job,
            lambda current: self._run_analyze(current, resource_ids, only_pending),
        )
        return job_schema(job)

    async def _collect_analysis_images(
        self,
        resource_ids: list[int] | None,
        only_pending: bool = True,
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
        if only_pending:
            stmt = stmt.where(
                text(
                    "NOT EXISTS ("
                    "SELECT 1 FROM ai_documents d "
                    "WHERE d.resource_id = resources.id AND d.status = 'ready'"
                    ")"
                )
            )
        rows = (await self.session.execute(stmt)).all()
        chosen: dict[int, Path] = {}
        for resource_id, raw_path in rows:
            if resource_id in chosen or not raw_path:
                continue
            path = Path(raw_path)
            if path.is_file():
                chosen[resource_id] = path
        return list(chosen.items())

    async def _analysis_contexts(self, resource_ids: list[int]) -> dict[int, dict]:
        if not resource_ids:
            return {}
        rows = (
            await self.session.execute(
                text(
                    "SELECT rt.resource_id, t.name FROM resource_tags rt "
                    "JOIN tags t ON t.id = rt.tag_id"
                )
            )
        ).all()
        tags: dict[int, list[str]] = {}
        for resource_id, name in rows:
            values = tags.setdefault(int(resource_id), [])
            if name and str(name) not in values:
                values.append(str(name))
        rows = (
            await self.session.execute(
                text(
                    "SELECT rc.resource_id, c.name FROM resource_categories rc "
                    "JOIN categories c ON c.id = rc.category_id"
                )
            )
        ).all()
        categories: dict[int, list[str]] = {}
        for resource_id, name in rows:
            values = categories.setdefault(int(resource_id), [])
            if name and str(name) not in values:
                values.append(str(name))
        rows = (
            await self.session.execute(
                text(
                    "SELECT rc.resource_id, c.name FROM resource_characters rc "
                    "JOIN characters c ON c.id = rc.character_id"
                )
            )
        ).all()
        characters: dict[int, list[str]] = {}
        for resource_id, name in rows:
            values = characters.setdefault(int(resource_id), [])
            if name and str(name) not in values:
                values.append(str(name))
        rows = (
            await self.session.execute(
                text(
                    "SELECT rp.resource_id, p.name FROM resource_persons rp "
                    "JOIN persons p ON p.id = rp.person_id"
                )
            )
        ).all()
        persons: dict[int, list[str]] = {}
        for resource_id, name in rows:
            values = persons.setdefault(int(resource_id), [])
            if name and str(name) not in values:
                values.append(str(name))
        wanted = set(resource_ids)
        result: dict[int, dict] = {}
        for resource_id in wanted:
            context = {
                "categories": categories.get(resource_id, [])[:8],
                "tags": tags.get(resource_id, [])[:12],
                "characters": characters.get(resource_id, [])[:5],
                "persons": persons.get(resource_id, [])[:5],
            }
            if any(context.values()):
                result[resource_id] = context
        return result

    @staticmethod
    def _failure_kind(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            body = exc.response.text.lower() if exc.response is not None else ""
            if "token repeat limit" in body:
                return "token_repeat_limit"
            return "ollama_http"
        if isinstance(exc, ValueError):
            return "invalid_json"
        if isinstance(exc, FileNotFoundError):
            return "image_missing"
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            return "ollama_unavailable"
        return type(exc).__name__

    @staticmethod
    def _archive_failure(
        job_id: str,
        resource_id: int,
        path: Path,
        kind: str,
        detail: str,
    ) -> None:
        root = settings.db_path.parent / "ai-failures" / job_id
        root.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image, ImageOps

            with Image.open(path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.thumbnail((320, 320), Image.Resampling.LANCZOS)
                image.save(root / f"{resource_id}.jpg", format="JPEG", quality=82)
        except Exception:
            pass
        (root / f"{resource_id}-error.txt").write_text(
            f"{kind}\n{detail}", encoding="utf-8"
        )
        manifest = root / "manifest.json"
        try:
            entries = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            entries = []
        entries.append(
            {
                "resource_id": resource_id,
                "path": str(path),
                "kind": kind,
                "error": detail[:4000],
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
        manifest.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    async def _run_analyze(
        self,
        job: Job,
        resource_ids: list[int] | None,
        only_pending: bool = True,
    ) -> None:
        factory = get_session_factory()
        async with factory() as session:
            service = AIService(session)
            images = await service._collect_analysis_images(resource_ids, only_pending)
            logger.info(
                "AI caption job %s started: total=%s only_pending=%s model=%s",
                job.id,
                len(images),
                only_pending,
                caption_provider.model,
            )
            jobs.update(
                job,
                total=len(images),
                done=0,
                failed=0,
                message="准备分析文案" if images else "没有待分析图片",
            )
            contexts = await service._analysis_contexts([rid for rid, _ in images])
            concurrency = await service.effective_concurrency()
            logger.info(
                "AI caption job %s concurrency=%s", job.id, concurrency
            )
            semaphore = asyncio.Semaphore(max(1, concurrency))

            async def analyze_one(resource_id: int, path: Path):
                async with semaphore:
                    try:
                        return await caption_provider.analyze(
                            path, contexts.get(resource_id)
                        )
                    except Exception as exc:  # noqa: BLE001 - returned to ordered loop
                        return exc

            tasks = [
                asyncio.create_task(analyze_one(rid, path)) for rid, path in images
            ]

            def cancel_pending() -> None:
                for task in tasks:
                    if not task.done():
                        task.cancel()

            failed = 0
            consecutive_failures = 0
            repeat_failures = 0
            for index, (resource_id, path) in enumerate(images, start=1):
                try:
                    result = await tasks[index - 1]
                    if isinstance(result, Exception):
                        raise result
                    document = result
                except Exception as exc:
                    kind = self._failure_kind(exc)
                    fallback_document = None
                    if kind == "token_repeat_limit" and anime_tagger.is_installed():
                        try:
                            fallback_document = await asyncio.to_thread(
                                anime_tagger.anime_tagger.analyze, path
                            )
                        except Exception as fallback_error:
                            logger.warning(
                                "anime fallback failed for resource %s: %s",
                                resource_id,
                                fallback_error,
                            )
                    if fallback_document is not None:
                        document = fallback_document
                        repeat_failures = 0
                        logger.info(
                            "AI caption job %s used anime fallback for resource=%s",
                            job.id,
                            resource_id,
                        )
                    else:
                        failed += 1
                        if kind == "token_repeat_limit":
                            repeat_failures += 1
                        else:
                            repeat_failures = 0
                        if isinstance(exc, (httpx.HTTPStatusError, ValueError)):
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                        detail = str(exc)
                        self._archive_failure(job.id, resource_id, path, kind, detail)
                        if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                            detail = f"{detail} | response={exc.response.text[:800]}"
                        logger.warning(
                            "AI caption job %s failed kind=%s resource=%s path=%s: %s",
                            job.id,
                            kind,
                            resource_id,
                            path,
                            detail,
                            exc_info=True,
                        )
                        jobs.update(
                            job,
                            done=index,
                            failed=failed,
                            message=f"已处理 {index}/{len(images)}，失败 {failed} 张：{exc}",
                        )
                        if consecutive_failures >= 3:
                            cancel_pending()
                            raise RuntimeError(
                                f"连续 {consecutive_failures} 张分析失败，任务已停止：{exc}"
                            ) from exc
                        if repeat_failures >= 10:
                            cancel_pending()
                            hint = (
                                "可安装 WD14 动漫标签模型作为兜底"
                                if not anime_tagger.is_installed()
                                else "WD14 兜底也未能处理这批图片"
                            )
                            raise RuntimeError(
                                "连续 10 张图片触发 token repeat limit；"
                                f"当前视觉模型可能不适合这批图片，任务已暂停。{hint}"
                            )
                        continue

                consecutive_failures = 0
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
                tag_source = "wd14" if document.model_id == anime_tagger.MODEL_ID else "vlm"
                for tag in dict.fromkeys(document.tags):
                    if not tag:
                        continue
                    await session.execute(
                        text(
                            "INSERT OR IGNORE INTO ai_tags "
                            "(resource_id, tag, category, confidence, source, model_id) "
                            "VALUES (:resource_id, :tag, NULL, NULL, :source, :model)"
                        ),
                        {
                            "resource_id": resource_id,
                            "tag": tag,
                            "source": tag_source,
                            "model": document.model_id,
                        },
                    )
                await session.commit()
                jobs.update(
                    job,
                    done=index,
                    failed=failed,
                    message=f"已分析 {index}/{len(images)}",
                )
            logger.info(
                "AI caption job %s finished: success=%s failed=%s",
                job.id,
                len(images) - failed,
                failed,
            )
            jobs.update(
                job,
                failed=failed,
                message=(
                    f"完成：成功 {len(images) - failed} 张，失败 {failed} 张"
                    if images
                    else "没有待分析图片"
                ),
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

    async def _caption_matches(self, terms: list[str]) -> dict[int, int]:
        cleaned: list[str] = []
        for term in terms:
            value = term.strip()
            if value and value not in cleaned:
                cleaned.append(value)
        if not cleaned:
            return {}
        conditions: list[str] = []
        params: dict[str, str] = {}
        for index, term in enumerate(cleaned):
            pattern = f"%{term.replace('%', '').replace('_', '')}%"
            params[f"term{index}"] = pattern
            conditions.append(
                f"(caption LIKE :term{index} OR short_caption LIKE :term{index} "
                f"OR tags_json LIKE :term{index} OR ocr_text LIKE :term{index})"
            )
        rows = (
            await self.session.execute(
                text(
                    "SELECT resource_id, caption, short_caption, tags_json, ocr_text "
                    "FROM ai_documents WHERE " + " OR ".join(conditions)
                ),
                params,
            )
        ).all()
        hits: dict[int, int] = {}
        for resource_id, caption, short_caption, tags_json, ocr_text in rows:
            haystack = " ".join(
                str(value or "")
                for value in (caption, short_caption, tags_json, ocr_text)
            )
            count = sum(1 for term in cleaned if term in haystack)
            if count:
                hits[int(resource_id)] = count
        return hits

    async def _feedback_adjustments(
        self, query: str, resource_ids: list[int]
    ) -> dict[int, float]:
        marks = await self._feedback_marks(query, resource_ids)
        return {
            resource_id: 0.03 if action == "relevant" else -0.05
            for resource_id, action in marks.items()
        }

    async def _feedback_marks(
        self, query: str, resource_ids: list[int], source: str = "search"
    ) -> dict[int, str]:
        if not resource_ids:
            return {}
        rows = (
            await self.session.execute(
                text(
                    "SELECT resource_id, action FROM ai_search_feedback "
                    "WHERE query = :query AND source = :source "
                    "AND action IN ('relevant', 'irrelevant') "
                    "ORDER BY id ASC"
                ),
                {"query": query.strip(), "source": source},
            )
        ).all()
        wanted = set(resource_ids)
        marks: dict[int, str] = {}
        for resource_id, action in rows:
            if int(resource_id) in wanted:
                marks[int(resource_id)] = str(action)
        return marks

    async def remove_feedback(
        self, query: str, resource_id: int, source: str = "search"
    ) -> None:
        if not query.strip():
            raise AIServiceError("反馈缺少查询文本", 400)
        await self.session.execute(
            text(
                "DELETE FROM ai_search_feedback "
                "WHERE query = :query AND resource_id = :resource_id AND source = :source "
                "AND action IN ('relevant', 'irrelevant')"
            ),
            {
                "query": query.strip(),
                "resource_id": resource_id,
                "source": source,
            },
        )
        await self.session.commit()
        operations_logger.info(
            "ai.feedback.remove query=%r resource_id=%s source=%s",
            query.strip(),
            resource_id,
            source,
        )

    async def add_feedback(
        self,
        query: str,
        resource_id: int,
        action: str,
        source: str = "search",
        score: float | None = None,
        position: int | None = None,
        features: dict | None = None,
    ) -> None:
        if action not in {"relevant", "irrelevant", "click"}:
            raise AIServiceError("不支持的反馈类型", 400)
        if not query.strip():
            raise AIServiceError("反馈缺少查询文本", 400)
        if action in {"relevant", "irrelevant"}:
            await self.session.execute(
                text(
                    "DELETE FROM ai_search_feedback "
                    "WHERE query = :query AND resource_id = :resource_id AND source = :source "
                    "AND action IN ('relevant', 'irrelevant')"
                ),
                {
                    "query": query.strip(),
                    "resource_id": resource_id,
                    "source": source,
                },
            )
        await self.session.execute(
            text(
                "INSERT INTO ai_search_feedback "
                "(query, resource_id, action, source, score, position, features_json) "
                "VALUES (:query, :resource_id, :action, :source, :score, :position, :features)"
            ),
            {
                "query": query.strip(),
                "resource_id": resource_id,
                "action": action,
                "source": source,
                "score": score,
                "position": position,
                "features": json.dumps(features or {}, ensure_ascii=False),
            },
        )
        await self.session.commit()
        operations_logger.info(
            "ai.feedback query=%r resource_id=%s action=%s source=%s",
            query.strip(),
            resource_id,
            action,
            source,
        )

    async def search(
        self, query: str, limit: int = 30, min_score: float = 0.0
    ) -> AISearchResponse:
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
        query_insight.notes.append("文案/标签命中会参与综合排序。")
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
        filters = [item.label for item in parsed.filters] + [
            f"标签={label}" for label in parsed.labels
        ]
        if not vectors:
            return AISearchResponse(
                items=[],
                scores=[],
                indexed=len(all_ids),
                matched=0,
                returned=0,
                filters=filters,
                query_insight=query_insight,
                min_score=max(0.0, min(1.0, min_score)),
            )

        caption_hits = await self._caption_matches([parsed.text, query])
        feedback = await self._feedback_adjustments(query, filtered_ids)
        matrix = np.stack(vectors)
        clip_scores = matrix @ text_vector.astype("float32")
        candidates: list[tuple[int, float, float, int, float]] = []
        filtered_low_score = 0
        for index, resource_id in enumerate(filtered_ids):
            clip_score = float(clip_scores[index])
            caption_hit = int(caption_hits.get(resource_id, 0))
            feedback_adjust = feedback.get(resource_id, 0.0)
            score = clip_score + min(0.12, caption_hit * 0.06) + feedback_adjust
            if score < min_score:
                filtered_low_score += 1
                continue
            candidates.append(
                (resource_id, clip_score, score, caption_hit, feedback_adjust)
            )
        candidates.sort(key=lambda item: item[2], reverse=True)
        explored = False
        if (
            len(candidates) > 10
            and random.random() < settings.search_exploration_rate
        ):
            replace_at = random.randint(4, min(9, len(candidates) - 1))
            from_tail = random.randint(10, len(candidates) - 1)
            candidates[replace_at], candidates[from_tail] = (
                candidates[from_tail],
                candidates[replace_at],
            )
            explored = True
        repo = ResourceRepository(self.session)
        items = []
        result_scores: list[float] = []
        result_ids: list[int] = []
        explanations = []
        for resource_id, clip_score, score, caption_hit, feedback_adjust in candidates:
            resource = await repo.get(resource_id)
            if resource is None:
                continue
            items.append(resource)
            result_scores.append(float(score))
            result_ids.append(resource_id)
            explanation = self._text_match_explanation(
                resource_id,
                {},
                parsed,
                clip_score,
            )
            if caption_hit:
                explanation.reasons.append("文案/标签命中")
            if feedback_adjust:
                explanation.reasons.append("历史反馈加权")
            explanations.append(explanation)
            if len(items) >= max(1, min(limit, 100)):
                break
        meta_by_id = await self._resource_meta(result_ids)
        for index, resource_id in enumerate(result_ids):
            meta = meta_by_id.get(resource_id)
            if meta:
                explanations[index].caption = str(meta.get("caption") or "")
                explanations[index].short_caption = str(meta.get("short_caption") or "")
                explanations[index].tags = list(meta.get("tags") or [])
                explanations[index].person_count = (
                    int(meta["person_count"])
                    if meta.get("person_count") is not None
                    else None
                )
                explanations[index].orientation = self._orientation_label(
                    meta.get("orientation")
                )
        return AISearchResponse(
            items=items,
            scores=result_scores,
            indexed=len(all_ids),
            matched=len(candidates),
            returned=len(items),
            filters=filters,
            query_insight=query_insight,
            explanations=explanations,
            min_score=max(0.0, min(1.0, min_score)),
            filtered_low_score=filtered_low_score,
            caption_matched=len(set(caption_hits) & set(filtered_ids)),
            feedback_adjusted=sum(1 for item in candidates if item[4]),
            feedback=await self._feedback_marks(query, result_ids),
            explored=explored,
        )
