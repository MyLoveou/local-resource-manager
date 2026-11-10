"""监视导入事件端点（前端轮询，检测新导入后刷新列表）。"""
from fastapi import APIRouter

from app.shared.utils.watch_events import watch_events

router = APIRouter()


@router.get("/watch-revision")
async def watch_revision() -> dict[str, object]:
    """监视导入修订号与最近类型；无导入时为 {revision: 0, type: null}。"""
    return watch_events.snapshot()
