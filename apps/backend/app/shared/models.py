"""API 契约基类（snake_case 字段 ↔ camelCase JSON）。

领域实体已按限界上下文归位：
- library 实体 → app.library.domain.models
- settings 实体 → app.settings.domain.models
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """API 契约基类：snake_case 字段 ↔ camelCase JSON。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StrictApiModel(ApiModel):
    """写入型请求模型：多出来的字段一律拒绝。

    `ApiModel` 默认忽略未知字段，曾导致「前端带了 season、旧后端不认识」
    时静默降级成资源级写入。写入路径必须显式失败，而不是猜。
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )
