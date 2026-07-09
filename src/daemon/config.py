from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_API_BASE_URL = "https://api.neuralnexus.site"


def is_placeholder_api_url(url: str) -> bool:
    """True for test/invalid API hosts that should not ship in user configs."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return True
    if host in {"api.example.test", "example.test", "localhost", "127.0.0.1"}:
        return True
    return host.endswith(".test") or host.endswith(".invalid")


def resolve_api_base_url(configured: str | None = None) -> str:
    return (
        os.getenv("NEURALNEXUS_API_BASE_URL")
        or configured
        or DEFAULT_API_BASE_URL
    ).rstrip("/")


def _default_config_dir() -> Path:
    override = os.getenv("NEURALNEXUS_MCP_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "neuralnexus-mcp"


CONFIG_DIR = _default_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"


@dataclass
class DaemonConfig:
    api_base_url: str = DEFAULT_API_BASE_URL
    watched_roots: list[str] = field(default_factory=list)
    device_secret: str | None = None
    device_id: str | None = None
    connection_mode: str = "relay"  # relay | tunnel | local
    public_base_url: str | None = None
    cloudflare_tunnel_token: str | None = None
    tunnel_mode: str = "auto"  # used only when connection_mode == tunnel
    local_port: int = 8000
    last_registered_at: str | None = None

    @classmethod
    def load(cls) -> DaemonConfig:
        if not CONFIG_PATH.exists():
            return cls()
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        config = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return config.normalize()

    def normalize(self) -> DaemonConfig:
        """Migrate legacy defaults so one-click install never requires Cloudflare."""
        changed = False
        if not self.connection_mode:
            self.connection_mode = "relay"
            changed = True
        if (
            self.connection_mode == "tunnel"
            and self.tunnel_mode == "auto"
            and not self.cloudflare_tunnel_token
            and not self.public_base_url
        ):
            self.connection_mode = "relay"
            changed = True
        if is_placeholder_api_url(self.api_base_url):
            resolved = resolve_api_base_url()
            if self.api_base_url != resolved:
                self.api_base_url = resolved
                changed = True
        if changed:
            self.save()
        return self

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def ensure_device_identity(self) -> None:
        changed = False
        if not self.device_id:
            self.device_id = secrets.token_urlsafe(12)
            changed = True
        if not self.device_secret:
            self.device_secret = f"mcp_dev_{secrets.token_urlsafe(32)}"
            changed = True
        if changed:
            self.save()

    def set_watched_roots(self, roots: list[str]) -> None:
        self.watched_roots = [str(Path(root).expanduser().resolve()) for root in roots]
        self.save()

    def add_watched_root(self, root: str) -> None:
        resolved = str(Path(root).expanduser().resolve())
        if resolved not in self.watched_roots:
            self.watched_roots.append(resolved)
            self.save()

    def primary_watch_root(self) -> str | None:
        return self.watched_roots[0] if self.watched_roots else None

    def mark_registered(self) -> None:
        self.last_registered_at = datetime.now(UTC).isoformat()
        self.save()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "api_base_url": self.api_base_url,
            "connection_mode": self.connection_mode,
            "device_id": self.device_id,
            "watched_roots": self.watched_roots,
            "public_base_url": self.public_base_url,
            "tunnel_mode": self.tunnel_mode,
            "local_port": self.local_port,
            "last_registered_at": self.last_registered_at,
            "has_api_key": CREDENTIALS_PATH.exists(),
            "config_dir": str(CONFIG_DIR),
        }


@dataclass
class Credentials:
    api_key: str

    @staticmethod
    def is_placeholder_api_key(api_key: str) -> bool:
        return api_key in {"sk-test-key", "test", ""} or api_key.startswith("sk-test")

    @classmethod
    def load(cls) -> Credentials | None:
        if not CREDENTIALS_PATH.exists():
            return None
        data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        api_key = data.get("api_key")
        if not api_key or cls.is_placeholder_api_key(api_key):
            return None
        return cls(api_key=api_key)

    @classmethod
    def save_api_key(cls, api_key: str) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_PATH.write_text(
            json.dumps({"api_key": api_key}, indent=2) + "\n",
            encoding="utf-8",
        )
        CREDENTIALS_PATH.chmod(0o600)

    def clear(self) -> None:
        if CREDENTIALS_PATH.exists():
            CREDENTIALS_PATH.unlink()
