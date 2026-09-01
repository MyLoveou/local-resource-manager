"""资源库仓储实现（SQLite）。

仓储在 snake_case（DB 列）与领域模型之间做映射；API 序列化交由 Pydantic 别名。
"""
import json
import sqlite3
from typing import Any

from app.shared.models import Resource, ResourceStatus, ResourceType

_RESOURCE_COLUMNS = """id, type, title, description, rating, cover_path, status,
    deleted_at, last_scraped_at, scraped_source, extra, created_at, updated_at"""


def _row_to_resource(row: sqlite3.Row) -> Resource:
    """DB 行 → 领域模型（extra 为 JSON 文本，类型/状态为枚举）。"""
    data = dict(row)
    data["extra"] = json.loads(data["extra"] or "{}")
    data["type"] = ResourceType(data["type"])
    data["status"] = ResourceStatus(data["status"])
    return Resource(**data)


class ResourceRepository:
    """资源仓储：创建/查询/统计。"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, resource: Resource) -> Resource:
        """插入并返回带 id 的完整实体。"""
        cur = self._conn.execute(
            """INSERT INTO resources
               (type, title, description, rating, cover_path, status, extra)
               VALUES (?,?,?,?,?,?,?)""",
            (
                resource.type.value,
                resource.title,
                resource.description,
                resource.rating,
                resource.cover_path,
                resource.status.value,
                json.dumps(resource.extra, ensure_ascii=False),
            ),
        )
        self._conn.commit()
        return self.get(cur.lastrowid)

    def get(self, resource_id: int) -> Resource | None:
        row = self._conn.execute(
            f"SELECT {_RESOURCE_COLUMNS} FROM resources WHERE id = ?", (resource_id,)
        ).fetchone()
        return _row_to_resource(row) if row else None

    def list(
        self,
        type_: ResourceType | None = None,
        status: ResourceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Resource]:
        """条件列表查询（type/status 可空），按创建时间倒序。"""
        sql = f"SELECT {_RESOURCE_COLUMNS} FROM resources WHERE 1=1"
        params: list[Any] = []
        if type_ is not None:
            sql += " AND type = ?"
            params.append(type_.value)
        if status is not None:
            sql += " AND status = ?"
            params.append(status.value)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_resource(r) for r in rows]

    def recent(self, limit: int = 12) -> list[Resource]:
        """最近入库的活跃资源。"""
        rows = self._conn.execute(
            f"""SELECT {_RESOURCE_COLUMNS} FROM resources
                WHERE status = ? ORDER BY created_at DESC LIMIT ?""",
            (ResourceStatus.ACTIVE.value, limit),
        ).fetchall()
        return [_row_to_resource(r) for r in rows]

    def stats(self) -> dict[str, int]:
        """资源统计（供概览）。"""
        row = self._conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN type='image' AND status='active' THEN 1 ELSE 0 END),0) AS image_count,
                 COALESCE(SUM(CASE WHEN type='video' AND status='active' THEN 1 ELSE 0 END),0) AS video_count,
                 COALESCE(SUM(CASE WHEN status='trashed' THEN 1 ELSE 0 END),0) AS trashed_count,
                 COALESCE(SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END),0) AS lost_count,
                 COALESCE((SELECT SUM(size) FROM files WHERE resource_id IN
                           (SELECT id FROM resources WHERE status='active')),0) AS total_size_bytes
               FROM resources"""
        ).fetchone()
        return dict(row)


class TaskSummaryRepository:
    """进行中任务计数（跨 scrape/download 表，只读）。"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def summary(self) -> dict[str, int]:
        row = self._conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM scrape_jobs WHERE status='running')  AS running_scrape_jobs,
                 (SELECT COUNT(*) FROM scrape_jobs WHERE status='failed')   AS failed_scrape_jobs,
                 (SELECT COUNT(*) FROM download_tasks WHERE status='running') AS active_downloads"""
        ).fetchone()
        return dict(row)
