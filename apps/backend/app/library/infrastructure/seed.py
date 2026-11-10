"""空库时写入演示资源，便于分页联调（扫描入库完成前）。"""
from app.library.infrastructure.demo_covers import local_cover_uri
from app.library.infrastructure.repositories import ResourceRepository
from app.library.domain.models import (
    Resource,
    ResourceStatus,
    ResourceType,
)

DEMO_IMAGE_COUNT = 200
DEMO_VIDEO_COUNT = 80
_PICSUM_PREFIX = "https://picsum.photos"


def _demo_resources() -> list[Resource]:
    images = [
        Resource(
            type=ResourceType.IMAGE,
            title=f"图片{i}",
            cover_path=local_cover_uri("图", i),
            status=ResourceStatus.ACTIVE,
        )
        for i in range(1, DEMO_IMAGE_COUNT + 1)
    ]
    videos = [
        Resource(
            type=ResourceType.VIDEO,
            title=f"视频{i}",
            cover_path=local_cover_uri("视", i),
            status=ResourceStatus.ACTIVE,
        )
        for i in range(1, DEMO_VIDEO_COUNT + 1)
    ]
    return images + videos


async def seed_demo_if_empty(repo: ResourceRepository) -> int:
    """库为空时插入演示数据，返回写入条数。"""
    if await repo.count() > 0:
        return 0
    return await repo.create_many(_demo_resources())


async def replace_remote_demo_covers(repo: ResourceRepository) -> int:
    """把已写入的 picsum 远程封面换成本地 SVG（已有库不必删库重建）。"""
    return await repo.rewrite_covers_starting_with(
        _PICSUM_PREFIX,
        lambda type_, row_id: local_cover_uri("图" if type_ == "image" else "视", row_id),
    )
