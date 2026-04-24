from __future__ import annotations

import os
from pathlib import Path

import yaml

import uvicorn


if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parent
    root_dir = backend_dir.parent
    system_file = root_dir / "config" / "system.yaml"
    system = {}
    if system_file.exists():
        system = yaml.safe_load(system_file.read_text(encoding="utf-8")) or {}
    host = os.getenv("COMPRESSOR_API_HOST", str(system.get("api_host", "127.0.0.1")))
    port = int(os.getenv("COMPRESSOR_API_PORT", str(system.get("api_port", 8000))))
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=[str(backend_dir / "app"), str(root_dir / "config")],
        reload_excludes=["*/node_modules/*", "*/__pycache__/*", "*.pyc"],
    )
