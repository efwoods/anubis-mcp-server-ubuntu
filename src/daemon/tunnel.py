from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_TUNNEL_URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


@dataclass
class TunnelHandle:
    mode: str
    public_base_url: str
    process: asyncio.subprocess.Process | None = None

    async def stop(self) -> None:
        if self.process is None:
            return
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()


async def start_tunnel(
    *,
    local_port: int,
    mode: str,
    public_base_url: str | None = None,
    tunnel_token: str | None = None,
) -> TunnelHandle:
    """Expose the local MCP HTTP server through Cloudflare or a fixed public URL."""
    normalized_mode = (mode or "auto").lower()

    if normalized_mode == "off":
        return TunnelHandle(
            mode="off",
            public_base_url=f"http://127.0.0.1:{local_port}",
        )

    if normalized_mode == "public_url" or public_base_url:
        if not public_base_url:
            raise ValueError("tunnel_mode=public_url requires public_base_url.")
        return TunnelHandle(mode="public_url", public_base_url=public_base_url.rstrip("/"))

    if normalized_mode == "token":
        if not tunnel_token:
            raise ValueError("tunnel_mode=token requires cloudflare_tunnel_token.")
        if shutil.which("cloudflared") is None:
            raise RuntimeError("cloudflared is not installed or not on PATH.")
        process = await asyncio.create_subprocess_exec(
            "cloudflared",
            "tunnel",
            "run",
            "--token",
            tunnel_token,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        if not public_base_url:
            raise ValueError(
                "public_base_url is required when using a named Cloudflare tunnel token."
            )
        return TunnelHandle(
            mode="token",
            public_base_url=public_base_url.rstrip("/"),
            process=process,
        )

    if shutil.which("cloudflared") is None:
        raise RuntimeError(
            "cloudflared is not installed. Use connection_mode=relay (default) "
            "or install cloudflared for optional tunnel mode."
        )

    process = await asyncio.create_subprocess_exec(
        "cloudflared",
        "tunnel",
        "--url",
        f"http://127.0.0.1:{local_port}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    public_url = await _wait_for_quick_tunnel_url(process)
    return TunnelHandle(mode="quick", public_base_url=public_url.rstrip("/"), process=process)


async def _wait_for_quick_tunnel_url(
    process: asyncio.subprocess.Process,
    *,
    timeout_seconds: float = 45.0,
) -> str:
    assert process.stdout is not None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while loop.time() < deadline:
        if process.returncode is not None:
            output = (await process.stdout.read()).decode("utf-8", errors="replace")
            raise RuntimeError(
                "cloudflared exited before publishing a tunnel URL.\n" + output
            )
        line = await asyncio.wait_for(process.stdout.readline(), timeout=2.0)
        if not line:
            continue
        text = line.decode("utf-8", errors="replace")
        match = _TUNNEL_URL_RE.search(text)
        if match:
            logger.info("Cloudflare quick tunnel ready at %s", match.group(0))
            return match.group(0)
    raise TimeoutError("Timed out waiting for cloudflared quick tunnel URL.")
