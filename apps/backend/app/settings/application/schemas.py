"""设置 API DTO。"""

from app.shared.models import ApiModel


class SecretState(ApiModel):
    configured: bool
    hint: str | None = None
    env_locked: bool = False


class MikanState(ApiModel):
    base_url: str
    env_locked: bool = False


class ScrapeSettingsOut(ApiModel):
    tmdb: SecretState
    bangumi: SecretState
    mikan: MikanState


class SystemSettingsOut(ApiModel):
    db_path: str
    library_path: str
    log_dir: str
    download_dir: str
    backup_dir: str
    backend_version: str


class ChannelSetting(ApiModel):
    mode: str
    command: str = ""


class ConsumeSettingsOut(ApiModel):
    channels: dict[str, ChannelSetting]


class SettingsView(ApiModel):
    scrape: ScrapeSettingsOut
    system: SystemSettingsOut
    consume: ConsumeSettingsOut


class ConsumeSettingsPatch(ApiModel):
    channels: dict[str, ChannelSetting]


class ScrapeSettingsPatch(ApiModel):
    tmdb_api_key: str | None = None
    bangumi_access_token: str | None = None
    mikan_base_url: str | None = None


class BackupResult(ApiModel):
    path: str


class SystemSettingPatch(ApiModel):
    db_path: str | None = None
    library_path: str | None = None
    log_dir: str | None = None
    download_dir: str | None = None
    backup_dir: str | None = None