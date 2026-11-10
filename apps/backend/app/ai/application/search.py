"""Search, similar-image, fusion and feedback use cases."""

from __future__ import annotations

import asyncio
import json
import random
import tempfile
from pathlib import Path

from sqlalchemy import select, text

from app.ai.application.errors import AIServiceError
from app.ai.application.jobs import jobs
from app.ai.application.labels import PROMPTS, select_labels
from app.ai.application.query import parse_query
from app.ai.application.schemas import (
    AIFusionResponse,
    AIMatchExplanation,
    AIQueryInsight,
    AISearchResponse,
    AISimilarResponse,
)
from app.ai.infrastructure.image_hash import dhash_many, hamming
from app.ai.infrastructure.model_store import MODEL_ID, is_installed
from app.ai.infrastructure.person_detector import person_detector
from app.ai.infrastructure.runtime import runtime
from app.library.domain.models import Resource, ResourceStatus, ResourceType
from app.library.infrastructure.orm import FileRow, ResourceRow
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.config import settings
from app.shared.log import operations_logger


class SearchMixin:
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
