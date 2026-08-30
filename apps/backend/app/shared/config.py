from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """共享配置（后端服务）。后续：token、数据库路径、SearXNG 地址、aria2/rqbit 地址等。"""

    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()
