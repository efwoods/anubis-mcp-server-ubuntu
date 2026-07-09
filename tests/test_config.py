from __future__ import annotations

import json
from pathlib import Path

from src.daemon.config import (
    CONFIG_PATH,
    CREDENTIALS_PATH,
    DEFAULT_API_BASE_URL,
    Credentials,
    DaemonConfig,
    is_placeholder_api_url,
)
from src.daemon.registrar import ApiRegistrar
from src.daemon.relay import relay_http_url, relay_ws_url


def test_daemon_config_round_trip(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    monkeypatch.setenv("NEURALNEXUS_MCP_CONFIG_DIR", str(config_dir))

    config = DaemonConfig.load()
    config.api_base_url = "https://api.example.test"
    config.connection_mode = "relay"
    config.set_watched_roots(["/tmp/data"])
    config.ensure_device_identity()
    config.save()

    reloaded = DaemonConfig.load()
    assert reloaded.api_base_url == "https://api.neuralnexus.site"
    assert reloaded.connection_mode == "relay"
    assert reloaded.watched_roots == [str(Path("/tmp/data").resolve())]
    assert reloaded.device_id
    assert reloaded.device_secret.startswith("mcp_dev_")
    assert CONFIG_PATH.exists()


def test_credentials_saved_with_restrictive_permissions(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    monkeypatch.setenv("NEURALNEXUS_MCP_CONFIG_DIR", str(config_dir))

    Credentials.save_api_key("sk-user-integration-key")
    assert CREDENTIALS_PATH.exists()
    assert oct(CREDENTIALS_PATH.stat().st_mode & 0o777) == oct(0o600)
    loaded = Credentials.load()
    assert loaded is not None
    assert loaded.api_key == "sk-user-integration-key"


def test_relay_registration_payload_shape(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    monkeypatch.setenv("NEURALNEXUS_MCP_CONFIG_DIR", str(config_dir))
    config = DaemonConfig.load()
    config.api_base_url = "https://api.example.test"
    config.connection_mode = "relay"
    config.set_watched_roots(["/tmp/watch"])
    config.ensure_device_identity()

    payload = ApiRegistrar.build_payload(
        config=config,
        server_name="Ubuntu-OS-Filesystem",
        mcp_path="/mcp",
    )
    body = payload.to_json()
    assert body["connection_mode"] == "relay"
    assert body["transport"] == "relay"
    assert body["mcp_url"] == relay_http_url("https://api.example.test", config.device_id or "")
    assert "discovery_url" not in body
    assert body["allowed_roots"] == [str(Path("/tmp/watch").resolve())]
    assert json.loads(json.dumps(body)) == body


def test_tunnel_registration_payload_shape(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    monkeypatch.setenv("NEURALNEXUS_MCP_CONFIG_DIR", str(config_dir))
    config = DaemonConfig.load()
    config.connection_mode = "tunnel"
    config.set_watched_roots(["/tmp/watch"])
    config.ensure_device_identity()

    payload = ApiRegistrar.build_payload(
        config=config,
        server_name="Ubuntu-OS-Filesystem",
        mcp_path="/mcp",
        public_base_url="https://demo.example.com",
    )
    body = payload.to_json()
    assert body["transport"] == "streamable_http"
    assert body["mcp_url"] == "https://demo.example.com/mcp"
    assert body["discovery_url"] == "https://demo.example.com/discovery"


def test_legacy_tunnel_config_migrates_to_relay(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    monkeypatch.setenv("NEURALNEXUS_MCP_CONFIG_DIR", str(config_dir))
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "api_base_url": "https://api.neuralnexus.site",
                "connection_mode": "tunnel",
                "tunnel_mode": "auto",
                "watched_roots": ["/tmp/data"],
            }
        ),
        encoding="utf-8",
    )

    config = DaemonConfig.load()
    assert config.connection_mode == "relay"


def test_placeholder_api_key_is_ignored(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    monkeypatch.setenv("NEURALNEXUS_MCP_CONFIG_DIR", str(config_dir))
    Credentials.save_api_key("sk-test-key")
    assert Credentials.load() is None


def test_placeholder_api_url_migrates_to_production(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    monkeypatch.setenv("NEURALNEXUS_MCP_CONFIG_DIR", str(config_dir))
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.json").write_text(
        json.dumps({"api_base_url": "https://api.example.test"}),
        encoding="utf-8",
    )

    config = DaemonConfig.load()
    assert config.api_base_url == DEFAULT_API_BASE_URL
    assert not is_placeholder_api_url(config.api_base_url)


def test_relay_ws_url() -> None:
    assert relay_ws_url("https://api.neuralnexus.site") == "wss://api.neuralnexus.site/mcp/relay"
    assert relay_ws_url("http://localhost:8000") == "ws://localhost:8000/mcp/relay"
