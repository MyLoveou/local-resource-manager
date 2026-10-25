"""Local AI vector search tests (no model download)."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.application.query import parse_query
from app.ai.application.service import AIService
from app.ai.infrastructure.model_store import MODEL_ID
from app.library.domain.models import Resource, ResourceStatus, ResourceType
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.db.migrations import migrate


class AISearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        # 这些用例用假向量验证检索逻辑，不该依赖本机是否装了 CLIP 模型。
        # CI 没下模型时 is_installed() 为假，AIService 会直接抛「请先安装 AI 模型」。
        self._model_patch = patch(
            "app.ai.application.service.is_installed", return_value=True
        )
        self._model_patch.start()
        self.addCleanup(self._model_patch.stop)
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.db_path = self.root / "t.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path.as_posix()}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def _resource(self, session, title: str) -> int:
        repo = ResourceRepository(session)
        resource = await repo.create(
            Resource(type=ResourceType.IMAGE, title=title, status=ResourceStatus.ACTIVE)
        )
        assert resource.id is not None
        await repo.add_file(
            resource.id,
            path=str(self.root / f"{title}.jpg"),
            sha256=f"{title:0<64}"[:64],
            size=3,
            format_="jpg",
            role="primary",
        )
        return resource.id

    def test_query_parser_extracts_hard_features(self) -> None:
        two = parse_query("两个人 室内")
        self.assertEqual(two.text, "室内")
        self.assertEqual([(item.feature, item.op, item.value) for item in two.filters], [("person_count", "eq", 2)])

        group = parse_query("合影 横图")
        self.assertEqual(group.text, "人物合影")
        self.assertEqual(
            [(item.feature, item.op, item.value) for item in group.filters],
            [("person_count", "gte", 2), ("orientation", "eq", "landscape")],
        )

        red_hat = parse_query("红帽子")
        self.assertEqual(red_hat.labels, ["红色帽子"])

    async def test_text_search_orders_by_cosine(self) -> None:
        vector_a = np.zeros(512, dtype="float32")
        vector_a[0] = 1
        vector_b = np.zeros(512, dtype="float32")
        vector_b[1] = 1
        query = vector_a.copy()

        async with self.factory() as session:
            first = await self._resource(session, "a")
            second = await self._resource(session, "b")
            for resource_id, vector in ((first, vector_a), (second, vector_b)):
                await session.execute(
                    text(
                        "INSERT INTO ai_vectors "
                        "(resource_id, model_id, dim, vector, source_path, updated_at) "
                        "VALUES (:rid, :model, 512, :vector, '', datetime('now'))"
                    ),
                    {"rid": resource_id, "model": MODEL_ID, "vector": vector.tobytes()},
                )
            await session.commit()

            with (
                patch("app.ai.application.service.is_installed", return_value=True),
                patch("app.ai.application.service.runtime.dependency_ready", return_value=True),
                patch("app.ai.application.service.runtime.encode_text", return_value=np.stack([query])),
            ):
                result = await AIService(session).search("a", 2)

        self.assertEqual([item.id for item in result.items], [first, second])
        self.assertAlmostEqual(result.scores[0], 1.0, places=5)
        self.assertAlmostEqual(result.scores[1], 0.0, places=5)
        self.assertIsNotNone(result.query_insight)
        self.assertEqual(result.query_insight.source, "text")
        self.assertEqual(result.query_insight.semantic_text, "a")
        self.assertEqual(len(result.explanations), 2)
        self.assertIn("CLIP 语义相似度", result.explanations[0].reasons[0])

    async def test_similar_excludes_self_and_finds_near_duplicate(self) -> None:
        vector = np.zeros(512, dtype="float32")
        vector[0] = 1

        async with self.factory() as session:
            first = await self._resource(session, "first")
            second = await self._resource(session, "second")
            for resource_id in (first, second):
                await session.execute(
                    text(
                        "INSERT INTO ai_vectors "
                        "(resource_id, model_id, dim, vector, source_path, updated_at) "
                        "VALUES (:rid, :model, 512, :vector, '', datetime('now'))"
                    ),
                    {"rid": resource_id, "model": MODEL_ID, "vector": vector.tobytes()},
                )
            await session.execute(
                text(
                    "INSERT INTO ai_hashes (resource_id, dhash, updated_at) "
                    "VALUES (:first, '00000000000000ff', datetime('now')), "
                    "(:second, '00000000000000fe', datetime('now'))"
                ),
                {"first": first, "second": second},
            )
            await session.commit()

            with (
                patch("app.ai.application.service.is_installed", return_value=True),
                patch("app.ai.application.service.runtime.dependency_ready", return_value=True),
            ):
                result = await AIService(session).similar(first, "auto", 10)

        self.assertEqual(result.items, [])
        self.assertEqual([item.id for item in result.duplicates], [second])
        self.assertNotIn(first, [item.id for item in result.duplicates])
        self.assertEqual(result.duplicate_scores[0], 1.0 - 1 / 64)
        self.assertIsNotNone(result.query_insight)
        self.assertEqual(result.query_insight.source, "image")
        self.assertEqual(result.duplicate_explanations[0].dhash_distance, 1)
        self.assertIn("近似重复", result.duplicate_explanations[0].reasons[0])

    async def test_fusion_excludes_source_and_returns_ranked_candidates(self) -> None:
        source_vec = np.zeros(512, dtype="float32")
        source_vec[0] = 1
        other_vec = source_vec.copy()
        text_vec = np.zeros(512, dtype="float32")
        text_vec[1] = 1

        async with self.factory() as session:
            source = await self._resource(session, "source")
            other = await self._resource(session, "other")
            third = await self._resource(session, "third")
            for resource_id, vector in (
                (source, source_vec),
                (other, other_vec),
                (third, text_vec),
            ):
                await session.execute(
                    text(
                        "INSERT INTO ai_vectors "
                        "(resource_id, model_id, dim, vector, source_path, updated_at) "
                        "VALUES (:rid, :model, 512, :vector, '', datetime('now'))"
                    ),
                    {"rid": resource_id, "model": MODEL_ID, "vector": vector.tobytes()},
                )
            await session.commit()

            with (
                patch("app.ai.application.service.is_installed", return_value=True),
                patch("app.ai.application.service.runtime.dependency_ready", return_value=True),
                patch(
                    "app.ai.application.service.runtime.encode_text",
                    return_value=np.stack([text_vec]),
                ),
            ):
                result = await AIService(session).fusion(source, "海边", 10)

        self.assertNotIn(source, [item.id for item in result.items])
        self.assertTrue(result.items)
        self.assertTrue(result.scores)

    async def test_count_filter_excludes_wrong_person_count(self) -> None:
        vector = np.zeros(512, dtype="float32")
        vector[0] = 1
        query = vector.copy()

        async with self.factory() as session:
            one = await self._resource(session, "one")
            two = await self._resource(session, "two")
            for resource_id, person_count in ((one, 1), (two, 2)):
                await session.execute(
                    text(
                        "INSERT INTO ai_vectors "
                        "(resource_id, model_id, dim, vector, source_path, updated_at) "
                        "VALUES (:rid, :model, 512, :vector, '', datetime('now'))"
                    ),
                    {"rid": resource_id, "model": MODEL_ID, "vector": vector.tobytes()},
                )
                await session.execute(
                    text(
                        "INSERT INTO ai_attributes "
                        "(resource_id, feature, value_json, value_num, model, updated_at) "
                        "VALUES (:rid, 'person_count', :json, :num, 'yolov8n', datetime('now'))"
                    ),
                    {"rid": resource_id, "json": str(person_count), "num": person_count},
                )
            await session.commit()

            with (
                patch("app.ai.application.service.is_installed", return_value=True),
                patch("app.ai.application.service.runtime.dependency_ready", return_value=True),
                patch("app.ai.application.service.runtime.encode_text", return_value=np.stack([query])),
            ):
                result = await AIService(session).search("两个人", 30)

        self.assertEqual([item.id for item in result.items], [two])
        self.assertEqual(result.matched, 1)
        self.assertEqual(result.returned, 1)
        self.assertEqual(result.filters, ["人数=2"])
        self.assertEqual(result.query_insight.person_count, 2)
        self.assertIn("人数=2", result.explanations[0].reasons)

    async def test_suggestions_include_thumbnail_and_tags(self) -> None:
        async with self.factory() as session:
            resource_id = await self._resource(session, "suggest")
            await session.execute(
                text(
                    "INSERT INTO ai_documents "
                    "(resource_id, caption, short_caption, tags_json, status) "
                    "VALUES (:rid, '猫耳角色', '猫耳', '[\"猫耳\"]', 'ready')"
                ),
                {"rid": resource_id},
            )
            await session.execute(
                text("INSERT INTO tags (name) VALUES ('猫耳')"),
            )
            await session.execute(
                text(
                    "INSERT INTO ai_tags (resource_id, tag, source) "
                    "VALUES (:rid, '猫耳', 'vlm')"
                ),
                {"rid": resource_id},
            )
            # 不在词表里的泛词不应进入建议（闭集）
            await session.execute(
                text(
                    "INSERT INTO ai_tags (resource_id, tag, source) "
                    "VALUES (:rid, '白色', 'vlm')"
                ),
                {"rid": resource_id},
            )
            await session.commit()
            result = await AIService(session).suggestions(10)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["resource_id"], resource_id)
        self.assertEqual(result[0]["thumbnail_path"], f"/library/resources/{resource_id}/content")
        self.assertIn("猫耳", result[0]["tags"])
        self.assertNotIn("白色", result[0]["tags"])

    async def test_feedback_replaces_and_can_be_removed(self) -> None:
        vector = np.zeros(512, dtype="float32")
        vector[0] = 1
        query = vector.copy()

        async with self.factory() as session:
            resource_id = await self._resource(session, "feedback")
            await session.execute(
                text(
                    "INSERT INTO ai_vectors "
                    "(resource_id, model_id, dim, vector, source_path, updated_at) "
                    "VALUES (:rid, :model, 512, :vector, '', datetime('now'))"
                ),
                {"rid": resource_id, "model": MODEL_ID, "vector": vector.tobytes()},
            )
            await session.commit()
            service = AIService(session)
            await service.add_feedback("cat", resource_id, "relevant")
            await service.add_feedback("cat", resource_id, "irrelevant")

            rows = (
                await session.execute(
                    text(
                        "SELECT action FROM ai_search_feedback "
                        "WHERE query = 'cat' AND resource_id = :rid"
                    ),
                    {"rid": resource_id},
                )
            ).scalars().all()
            self.assertEqual(list(rows), ["irrelevant"])

            with (
                patch("app.ai.application.service.is_installed", return_value=True),
                patch("app.ai.application.service.runtime.dependency_ready", return_value=True),
                patch("app.ai.application.service.runtime.encode_text", return_value=np.stack([query])),
            ):
                result = await service.search("cat", 10)
            self.assertEqual(result.feedback, {resource_id: "irrelevant"})

            await service.remove_feedback("cat", resource_id)
            rows = (
                await session.execute(
                    text(
                        "SELECT action FROM ai_search_feedback "
                        "WHERE query = 'cat' AND resource_id = :rid"
                    ),
                    {"rid": resource_id},
                )
            ).scalars().all()
            self.assertEqual(list(rows), [])
