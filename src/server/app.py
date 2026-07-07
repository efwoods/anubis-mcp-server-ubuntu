import asyncio
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from fastmcp.resources import DirectoryResource
from dotenv import load_dotenv
import os
load_dotenv()
HEALTH_DATA_ROOT = Path(
    os.getenv(
        "HEALTH_DATA_DIR",
        "/home/user/Documents/Health Auto Export/health_metric_data",
    )
).resolve()
ALLOWED_ROOTS = [HEALTH_DATA_ROOT]  # widen if needed

mcp = FastMCP("Ubuntu-OS-Filesystem")

def _resolve_allowed_path(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if ALLOWED_ROOTS and not any(path.is_relative_to(root) for root in ALLOWED_ROOTS):
        raise ResourceError(f"Path not allowed: {path_str}")
    return path
def _resolve_allowed_dir(directory: str) -> Path:
    path = _resolve_allowed_path(directory)
    if not path.is_dir():
        raise ResourceError(f"Not a directory: {directory}")
    return path
def _resolve_allowed_file(file_path: str) -> Path:
    path = _resolve_allowed_path(file_path)
    if not path.is_file():
        raise ResourceError(f"Not a file: {file_path}")
    return path

@mcp.tool()
async def list_all_files(directory: str, recursive: bool = True) -> list[str]:
    """List all files under the given directory. Discover CSV/JSON exports."""
    root = _resolve_allowed_dir(directory)
    def _list_files() -> list[str]:
        if recursive:
            return sorted(str(p) for p in root.rglob("*") if p.is_file())
        return sorted(str(p) for p in root.iterdir() if p.is_file())
    return await asyncio.to_thread(_list_files)

@mcp.tool()
async def read_file_bytes(file_path: str) -> str:
    """Return base64-encoded file bytes for sandbox upload."""
    path = _resolve_allowed_file(file_path)
    def _read() -> str:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    return await asyncio.to_thread(_read)

@mcp.tool()
async def get_file_info(file_path: str) -> dict:
    """Return size, extension, and modified date for a file."""
    path = _resolve_allowed_file(file_path)
    stat = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "extension": path.suffix,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }

@mcp.tool()
async def preview_data(file_path: str, n_rows: int = 5) -> dict:
    """Return a small preview of CSV/JSON data."""
    path = _resolve_allowed_file(file_path)
    suffix = path.suffix.lower()
    def _preview() -> dict:
        if suffix == ".csv":
            df = pd.read_csv(path, nrows=n_rows)
        elif suffix == ".json":
            df = pd.read_json(path)
            df = df.head(n_rows)
        else:
            if suffix == ".txt":
                return path.read_text()[:10]
            else:
                raise ResourceError("Only CSV and JSON previews are supported.")
        return {
            "path": str(path),
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
        }
    return await asyncio.to_thread(_preview)

# Optional: batch helper for client
@mcp.tool()
async def read_files_for_sandbox(file_paths: list[str]) -> list[dict]:
    """Read multiple files as base64 payloads for sandbox upload."""
    results = []
    for fp in file_paths:
        info = await get_file_info(fp)
        content_b64 = await read_file_bytes(fp)
        results.append({**info, "content_b64": content_b64})
    return results

if HEALTH_DATA_ROOT.is_dir():
    mcp.add_resource(
        DirectoryResource(
            uri="health://files",
            path=HEALTH_DATA_ROOT,
            name="Health Data Files",
            description="List files in the health metric data folder.",
            recursive=True,
        )
    )

if __name__ == "__main__":
    mcp.run(transport="streamable-http")