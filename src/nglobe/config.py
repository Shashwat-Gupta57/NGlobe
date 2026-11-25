"""Centralized configuration for NGlobe.

Defaults live here. An optional config.toml (next to this file, or
~/.nglobe/config.toml for user overrides) and NETWORKGLOBE_* environment
variables can override them, e.g. NETWORKGLOBE_PROXY__LISTEN_PORT=9999.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

from nglobe.utils.resource_path import get_resource_path

HOME = Path.home() / ".nglobe"


class ProxyConfig(BaseModel):
    listen_host: str = "127.0.0.1"
    listen_port: int = 8888
    ssl_insecure: bool = False
    set_system_proxy: bool = True  # false: point apps at the proxy yourself
    cert_dir: str = str(Path.home() / ".mitmproxy")  # mitmproxy's default, so an already-trusted CA keeps working


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8085
    log_level: str = "INFO"
    open_browser_on_start: bool = True


class GeoIPConfig(BaseModel):
    # Downloaded databases go here; bundled ones in the package are the fallback.
    city_db_path: str = str(HOME / "geoip" / "GeoLite2-City.mmdb")
    asn_db_path: str = str(HOME / "geoip" / "GeoLite2-ASN.mmdb")
    cache_size: int = 10_000


class DatabaseConfig(BaseModel):
    sqlite_path: str = str(HOME / "data" / "networkglobe.db")


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "pretty"  # "pretty" | "structured"
    file: str = str(HOME / "logs" / "networkglobe.log")
    max_size_mb: int = 10
    backup_count: int = 3


class PerformanceConfig(BaseModel):
    pipeline_batch_size: int = 50
    pipeline_flush_interval_ms: int = 500
    max_ws_queue_size: int = 1000


class CaptureConfig(BaseModel):
    ignored_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "::1"])
    max_path_length: int = 500


class LocationConfig(BaseModel):
    auto_detect: bool = True
    latitude: float = 0.0
    longitude: float = 0.0


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETWORKGLOBE_", env_nested_delimiter="__", extra="ignore")

    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    geoip: GeoIPConfig = Field(default_factory=GeoIPConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    location: LocationConfig = Field(default_factory=LocationConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Earlier sources win: env > user toml > bundled toml > defaults
        tomls = [p for p in (HOME / "config.toml", get_resource_path("config.toml")) if p.exists()]
        return (init_settings, env_settings, *(TomlConfigSettingsSource(settings_cls, toml_file=p) for p in tomls))


def load_config() -> AppConfig:
    return AppConfig()
