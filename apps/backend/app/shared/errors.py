"""领域层异常。"""


class DomainError(Exception):
    """领域层异常基类。"""


class InvalidStateError(DomainError):
    """非法状态迁移（由领域方法在状态机边界处抛出）。"""
