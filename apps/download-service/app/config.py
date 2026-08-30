from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """下载服务配置（后续：aria2 RPC 地址、rqbit HTTP 地址、并发/限速默认值等）。"""

    host: str = "127.0.0.1"
    port: int = 8002
    token: str = ""


settings = Settings()
