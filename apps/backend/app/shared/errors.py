"""领域层异常。"""


class DomainError(Exception):
    """领域层异常基类。"""


class InvalidStateError(DomainError):
    """非法状态迁移（由领域方法在状态机边界处抛出）。"""


class DownloadError(Exception):
    """URL/网络校验错误（SSRF 等；原属 download 应用，D-20261007-01 迁至 shared）。"""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code
