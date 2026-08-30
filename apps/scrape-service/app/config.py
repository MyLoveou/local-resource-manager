from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """抓取服务配置（后续：SearXNG 地址、token、缓存目录等）。"""

    host: str = "127.0.0.1"
    port: int = 8001
    token: str = ""


settings = Settings()
