"""AI model status, indexing and semantic search."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import httpx
from pathlib import Path

from sqlalchemy import case, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.application.errors import AIServiceError
from app.ai.application.jobs import Job, jobs
from app.ai.application.labels import PROMPTS, select_labels
from app.ai.application.query import AttributeFilter
from app.ai.application.search import SearchMixin
from app.ai.application.schemas import (
    AIJob,
    AIModelInfo,
    AIDeviceInfo,
    AIPerformance,
    AIPerformancePatch,
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
from app.ai.infrastructure.image_hash import dhash_many
from app.ai.infrastructure.person_detector import person_detector
from app.ai.infrastructure.runtime import runtime
from app.library.domain.models import ResourceStatus, ResourceType
from app.library.infrastructure.orm import FileRow, ResourceRow
from app.shared.config import settings
from app.shared.db.db import get_session_factory
from app.shared.log import logger, operations_logger

INDEX_BATCH_SIZE = 8


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


class AIService(SearchMixin):
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
        info = await asyncio.to_thread(device_hints.device_info)
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
        wanted = set(resource_ids)
        if not wanted:
            return {}
        params = {f"id{index}": resource_id for index, resource_id in enumerate(wanted)}
        placeholders = ", ".join(f":id{index}" for index in range(len(wanted)))
        rows = (
            await self.session.execute(
                text(
                    "SELECT rt.resource_id, t.name FROM resource_tags rt "
                    "JOIN tags t ON t.id = rt.tag_id "
                    f"WHERE rt.resource_id IN ({placeholders})"
                ),
                params,
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
                    "JOIN categories c ON c.id = rc.category_id "
                    f"WHERE rc.resource_id IN ({placeholders})"
                ),
                params,
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
                    "JOIN characters c ON c.id = rc.character_id "
                    f"WHERE rc.resource_id IN ({placeholders})"
                ),
                params,
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
                    "JOIN persons p ON p.id = rp.person_id "
                    f"WHERE rp.resource_id IN ({placeholders})"
                ),
                params,
            )
        ).all()
        persons: dict[int, list[str]] = {}
        for resource_id, name in rows:
            values = persons.setdefault(int(resource_id), [])
            if name and str(name) not in values:
                values.append(str(name))
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
                        await asyncio.to_thread(
                            self._archive_failure, job.id, resource_id, path, kind, detail
                        )
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
