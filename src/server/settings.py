from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ServerSettings:
    host: str
    port: int
    mcp_path: str
    health_data_dir: Path
    server_name: str
    device_secret: str | None
    public_base_url: str | None
    require_device_auth: bool

    @classmethod
    def from_env(cls, *, device_secret: str | None = None) -> ServerSettings:
        health_root = Path(
            os.getenv(
                "HEALTH_DATA_DIR",
                "/home/user/Documents/Health Auto Export/health_metric_data",
            )
        ).resolve()
        return cls(
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", os.getenv("MCP_PORT", "8000"))),
            mcp_path=os.getenv("MCP_PATH", "/mcp"),
            health_data_dir=health_root,
            server_name=os.getenv("MCP_SERVER_NAME", "Ubuntu-OS-Filesystem"),
            device_secret=device_secret or os.getenv("MCP_DEVICE_SECRET"),
            public_base_url=os.getenv("PUBLIC_BASE_URL"),
            require_device_auth=_env_bool("MCP_REQUIRE_DEVICE_AUTH", True),
        )

    @property
    def allowed_roots(self) -> tuple[Path, ...]:
        return (self.health_data_dir,)

    def local_mcp_url(self) -> str:
        return f"http://{self.host}:{self.port}{self.mcp_path}"

    def local_discovery_url(self) -> str:
        return f"http://{self.host}:{self.port}/discovery"

    def public_mcp_url(self, public_base_url: str | None = None) -> str:
        base = (public_base_url or self.public_base_url or "").rstrip("/")
        if not base:
            return self.local_mcp_url()
        return f"{base}{self.mcp_path}"

    def public_discovery_url(self, public_base_url: str | None = None) -> str:
        base = (public_base_url or self.public_base_url or "").rstrip("/")
        if not base:
            return self.local_discovery_url()
        return f"{base}/discovery"
