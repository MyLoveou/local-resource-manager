"""资源库应用 DTO（API 契约，继承 ApiModel 以输出 camelCase）。"""
from app.shared.models import ApiModel, Resource


class ResourceStats(ApiModel):
    """资源统计。"""

    image_count: int = 0
    video_count: int = 0
    total_size_bytes: int = 0
    trashed_count: int = 0
    lost_count: int = 0


class TaskSummary(ApiModel):
    """进行中任务概览。"""

    running_scrape_jobs: int = 0
    failed_scrape_jobs: int = 0
    active_downloads: int = 0


class Overview(ApiModel):
    """首页概览（统计 + 最近添加 + 任务）。"""

    stats: ResourceStats
    recent: list[Resource]
    tasks: TaskSummary
