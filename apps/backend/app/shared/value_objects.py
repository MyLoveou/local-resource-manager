"""值对象（Value Object）：不可变、按值语义、内聚校验与行为。

实体保留原始列以适配 DB/API；值对象作为"行为透镜"由实体属性暴露（只读视图）。
"""
from dataclasses import dataclass
from typing import Annotated

from pydantic import Field

# 评分约束类型值对象：0-10
Rating = Annotated[float, Field(ge=0, le=10)]


@dataclass(frozen=True)
class Dimension:
    """宽高值对象：内聚宽高比等计算。"""

    width: int
    height: int

    @property
    def aspect_ratio(self) -> float:
        """宽高比。"""
        return self.width / self.height


@dataclass(frozen=True)
class Progress:
    """下载进度值对象（不可变，替换而非修改）。"""

    downloaded: int
    total: int | None
    speed: int = 0

    @property
    def percent(self) -> float | None:
        """进度百分比 0-100；总量未知返回 None。"""
        if self.total and self.total > 0:
            return min(100.0, self.downloaded / self.total * 100)
        return None
