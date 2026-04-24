from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

from app.domain.models import IoTemplate, StationIoMapping


class ConfigStore:
    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.overrides_file = self.config_dir / "station_overrides.yaml"
        self.templates_file = self.config_dir / "io_templates.yaml"
        self.system_file = self.config_dir / "system.yaml"
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        if not self.overrides_file.exists():
            self.overrides_file.write_text(yaml.safe_dump({"mappings": []}), encoding="utf-8")
        if not self.templates_file.exists():
            self.templates_file.write_text(yaml.safe_dump({"templates": []}), encoding="utf-8")
        if not self.system_file.exists():
            self.system_file.write_text(
                yaml.safe_dump(
                    {
                        "simulation": False,
                        "log_dir": "data",
                        "driver": "ni",
                        "api_host": "127.0.0.1",
                        "api_port": 8000,
                        "cors_origins": ["*"],
                    }
                ),
                encoding="utf-8",
            )

    def load_station_overrides(self) -> Dict[int, StationIoMapping]:
        raw = yaml.safe_load(self.overrides_file.read_text(encoding="utf-8")) or {}
        mappings = raw.get("mappings", [])
        return {item["stationId"]: StationIoMapping(**item) for item in mappings}

    def save_station_overrides(self, mappings: Dict[int, StationIoMapping]) -> None:
        payload = {"mappings": [m.model_dump(mode="json") for _, m in sorted(mappings.items(), key=lambda x: x[0])]}
        self.overrides_file.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def list_templates(self) -> List[IoTemplate]:
        raw = yaml.safe_load(self.templates_file.read_text(encoding="utf-8")) or {}
        return [IoTemplate(**item) for item in raw.get("templates", [])]

    def save_templates(self, templates: List[IoTemplate]) -> None:
        payload = {"templates": [t.model_dump(mode="json") for t in templates]}
        self.templates_file.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    def load_system(self) -> dict:
        return yaml.safe_load(self.system_file.read_text(encoding="utf-8")) or {}

    def save_system(self, data: dict) -> None:
        self.system_file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
