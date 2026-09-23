"""下载 API DTO。"""

from app.shared.models import ApiModel


class DownloadTaskCreate(ApiModel):
    url: str
