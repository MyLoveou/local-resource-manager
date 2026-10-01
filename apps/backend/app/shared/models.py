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
