"""Centralized configuration system for NetworkGlobe.

Loads settings from config.toml and exposes typed access to every subsystem.
All configuration sections map to Pydantic models — no scattered constants.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource

try:
    from pydantic_settings import TomlConfigSettingsSource
except ImportError:
    TomlConfigSettingsSource = None  # type: ignore[assignment,misc]


def _find_config_path() -> Path:
    """Resolve the path to config.toml relative to the application root."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent
    return base / "config.toml"


# ── Section Models ──────────────────────────────────────────────


class ProxyConfig(BaseModel):
    listen_host: str = "127.0.0.1"
    listen_port: int = 8888
    ssl_insecure: bool = False
    cert_dir: str = "~/.networkglobe/certs"


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    log_level: str = "INFO"
    open_browser_on_start: bool = True


class GeoIPConfig(BaseModel):
    city_db_path: str = "geoip/data/GeoLite2-City.mmdb"
    asn_db_path: str = "geoip/data/GeoLite2-ASN.mmdb"
    cache_size: int = 10_000


class DatabaseConfig(BaseModel):
    backend: Literal["sqlite", "postgres"] = "sqlite"
    sqlite_path: str = "data/networkglobe.db"
    postgres_url: str = ""


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: Literal["structured", "pretty"] = "pretty"
    file: str = "logs/networkglobe.log"
    max_size_mb: int = 50
    backup_count: int = 3


class ThemeConfig(BaseModel):
    mode: Literal["dark", "light"] = "dark"
    accent_color: str = "#6366f1"
    map_style: Literal["dark", "light", "satellite"] = "dark"


class AnimationsConfig(BaseModel):
    arc_duration_ms: int = 2000
    arc_fade_ms: int = 5000
    pulse_duration_ms: int = 1500
    enable_animations: bool = True
    max_visible_arcs: int = 500


class PerformanceConfig(BaseModel):
    pipeline_batch_size: int = 50
    pipeline_flush_interval_ms: int = 500
    ws_batch_threshold: int = 10
    ws_batch_interval_ms: int = 100
    max_ws_queue_size: int = 1000
    frontend_ring_buffer_size: int = 1000


class CaptureConfig(BaseModel):
    ignored_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "*.networkglobe.local"]
    )
    capture_connect: bool = True
    max_path_length: int = 500


class LocationConfig(BaseModel):
    auto_detect: bool = True
    latitude: float = 0.0
    longitude: float = 0.0


# ── Root Configuration ──────────────────────────────────────────


class AppConfig(BaseSettings):
    """Root configuration aggregating all subsystem settings.

    Loads from config.toml at the application root. Environment variables
    can override any setting using the NETWORKGLOBE_ prefix with double
    underscores for nesting (e.g., NETWORKGLOBE_PROXY__LISTEN_PORT=9999).
    """

    model_config = SettingsConfigDict(
        env_prefix="NETWORKGLOBE_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    geoip: GeoIPConfig = Field(default_factory=GeoIPConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    animations: AnimationsConfig = Field(default_factory=AnimationsConfig)
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
        """Add TOML file as a settings source (lowest priority)."""
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,
            env_settings,
        ]
        config_path = _find_config_path()
        if TomlConfigSettingsSource is not None and config_path.exists():
            sources.append(
                TomlConfigSettingsSource(settings_cls, toml_file=config_path)
            )
        return tuple(sources)


def load_config() -> AppConfig:
    """Load and return the application configuration.

    This is the single entry point for configuration access.
    All subsystems should receive their config via dependency injection,
    not by calling this function directly.
    """
    return AppConfig()  # type: ignore[call-arg]

