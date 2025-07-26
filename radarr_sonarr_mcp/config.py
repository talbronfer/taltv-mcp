from __future__ import annotations

"""Configuration dataclasses and helpers."""

from dataclasses import dataclass
from typing import Any
import json
import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()


def _default_ip() -> str:
    return os.environ.get("NAS_IP", "10.0.0.23")


@dataclass
class NasConfig:
    """Configuration for the NAS or server hosting Radarr/Sonarr."""

    ip: str = _default_ip()
    port: str = "7878"


@dataclass
class RadarrConfig:
    api_key: str = ""
    base_path: str = "/api/v3"
    port: str = "7878"
    ip: str = _default_ip()

    @property
    def base_url(self) -> str:
        return f"http://{self.ip}:{self.port}{self.base_path}"


@dataclass
class SonarrConfig:
    api_key: str = ""
    base_path: str = "/api/v3"
    port: str = "8989"
    ip: str = _default_ip()

    @property
    def base_url(self) -> str:
        return f"http://{self.ip}:{self.port}{self.base_path}"


@dataclass
class ServerConfig:
    port: int = 3000


@dataclass
class Config:
    nas_config: NasConfig
    radarr_config: RadarrConfig
    sonarr_config: SonarrConfig
    server_config: ServerConfig


def load_config(path: str | None = None) -> Config:
    """Load configuration from ``path`` or environment variables."""
    if path is None and (
        os.environ.get("RADARR_API_KEY") or os.environ.get("SONARR_API_KEY")
    ):
        nas_ip = os.environ.get("NAS_IP", "10.0.0.23")
        config_data: dict[str, Any] = {
            "nasConfig": {"ip": nas_ip, "port": os.environ.get("RADARR_PORT", "7878")},
            "radarrConfig": {
                "apiKey": os.environ.get("RADARR_API_KEY", ""),
                "basePath": os.environ.get("RADARR_BASE_PATH", "/api/v3"),
                "port": os.environ.get("RADARR_PORT", "7878"),
            },
            "sonarrConfig": {
                "apiKey": os.environ.get("SONARR_API_KEY", ""),
                "basePath": os.environ.get("SONARR_BASE_PATH", "/api/v3"),
                "port": os.environ.get("SONARR_PORT", "8989"),
            },
            "server": {"port": int(os.environ.get("MCP_SERVER_PORT", "3000"))},
        }
    else:
        path = path or "config.json"
        with open(path, "r") as f:
            config_data = json.load(f)

    nas_conf = config_data.get("nasConfig", {})
    nas = NasConfig(**nas_conf)

    radarr_conf = config_data.get("radarrConfig", {})
    radarr = RadarrConfig(
        api_key=radarr_conf.get("apiKey", ""),
        base_path=radarr_conf.get("basePath", "/api/v3"),
        port=radarr_conf.get("port", "7878"),
        ip=nas.ip,
    )

    sonarr_conf = config_data.get("sonarrConfig", {})
    sonarr = SonarrConfig(
        api_key=sonarr_conf.get("apiKey", ""),
        base_path=sonarr_conf.get("basePath", "/api/v3"),
        port=sonarr_conf.get("port", "8989"),
        ip=nas.ip,
    )

    server_conf = config_data.get("server", {})
    server = ServerConfig(port=server_conf.get("port", 3000))
    return Config(nas, radarr, sonarr, server)


def save_config(config: Config, path: str = "config.json") -> None:
    """Save configuration to ``path``."""
    data = {
        "nasConfig": {
            "ip": config.nas_config.ip,
            "port": config.nas_config.port,
        },
        "radarrConfig": {
            "apiKey": config.radarr_config.api_key,
            "basePath": config.radarr_config.base_path,
            "port": config.radarr_config.port,
        },
        "sonarrConfig": {
            "apiKey": config.sonarr_config.api_key,
            "basePath": config.sonarr_config.base_path,
            "port": config.sonarr_config.port,
        },
        "server": {"port": config.server_config.port},
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def save_env(config: Config, path: str = ".env") -> None:
    """Save configuration to an environment file."""
    lines = [
        f"NAS_IP={config.nas_config.ip}",
        f"RADARR_PORT={config.radarr_config.port}",
        f"SONARR_PORT={config.sonarr_config.port}",
        f"RADARR_API_KEY={config.radarr_config.api_key}",
        f"RADARR_BASE_PATH={config.radarr_config.base_path}",
        f"SONARR_API_KEY={config.sonarr_config.api_key}",
        f"SONARR_BASE_PATH={config.sonarr_config.base_path}",
        f"MCP_SERVER_PORT={config.server_config.port}",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

