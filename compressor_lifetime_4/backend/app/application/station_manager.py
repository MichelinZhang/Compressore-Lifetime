from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from app.adapters.base import AoIoDriver
from app.adapters.ni_daq import NiDaqDriver
from app.adapters.simulated import SimulatedDriver
from app.application.test_runner import StationRunner
from app.domain.models import (
    Direction,
    IoTemplate,
    LogicalSignal,
    PhysicalChannelRef,
    StationConfig,
    StationIoMapping,
    StationRuntime,
    StationStatus,
    StationView,
    ValidateMappingResponse,
    ValidationIssue,
)
from app.infrastructure.channel_registry import ChannelRegistry
from app.infrastructure.config_store import ConfigStore
from app.infrastructure.csv_logger import CsvLogger
from app.infrastructure.event_bus import EventBus


def default_mapping(station_id: int, device: str = "Dev1") -> StationIoMapping:
    return StationIoMapping(
        stationId=station_id,
        templateId="legacy-ni-default",
        version=1,
        bindings={
            LogicalSignal.V1: PhysicalChannelRef(device=device, moduleType="DO", channel=0, direction="OUT", invert=False),
            LogicalSignal.V2: PhysicalChannelRef(device=device, moduleType="DO", channel=1, direction="OUT", invert=False),
            LogicalSignal.V3: PhysicalChannelRef(device=device, moduleType="DO", channel=2, direction="OUT", invert=False),
            LogicalSignal.COMPRESSOR: PhysicalChannelRef(device=device, moduleType="DO", channel=3, direction="OUT", invert=False),
            LogicalSignal.P_SENSOR: PhysicalChannelRef(device=device, moduleType="AI", channel=0, direction="IN", invert=False),
            LogicalSignal.COUNTER_PWR: PhysicalChannelRef(device=device, moduleType="DO", channel=5, direction="OUT", invert=False),
            LogicalSignal.COUNTER_SIG: PhysicalChannelRef(device=device, moduleType="DO", channel=6, direction="OUT", invert=False),
            LogicalSignal.BUZZER: PhysicalChannelRef(device=device, moduleType="DO", channel=7, direction="OUT", invert=False),
        },
    )


@dataclass
class StationEntity:
    config: StationConfig
    mapping: StationIoMapping
    runtime: StationRuntime
    runner: StationRunner | None = None


class StationManager:
    def __init__(self, store: ConfigStore, bus: EventBus, root_dir: Path) -> None:
        self._lock = asyncio.Lock()
        self.store = store
        self.bus = bus
        self.root_dir = root_dir
        self.registry = ChannelRegistry()
        self.system = self.store.load_system()
        self.driver: AoIoDriver = SimulatedDriver() if self.system.get("simulation", False) else NiDaqDriver()
        self.logger = CsvLogger(root_dir / self.system.get("log_dir", "data"))
        self.stations: Dict[int, StationEntity] = {}
        self.mappings = self.store.load_station_overrides()
        self.templates = self.store.list_templates()
        self._next_station = 1
        self.add_station()

    def _ensure_mapping(self, station_id: int, device: str) -> StationIoMapping:
        mapping = self.mappings.get(station_id)
        if mapping:
            return mapping
        mapping = default_mapping(station_id, device)
        self.mappings[station_id] = mapping
        self.store.save_station_overrides(self.mappings)
        return mapping

    def list_stations(self) -> List[StationView]:
        return [StationView(config=s.config, runtime=s.runtime, mapping=s.mapping) for _, s in sorted(self.stations.items())]

    def add_station(self) -> StationView:
        station_id = self._next_station
        self._next_station += 1
        config = StationConfig(stationId=station_id)
        mapping = self._ensure_mapping(station_id, config.deviceName)
        entity = StationEntity(config=config, mapping=mapping, runtime=StationRuntime())
        self.stations[station_id] = entity
        return StationView(config=config, runtime=entity.runtime, mapping=mapping)

    def remove_station(self, station_id: int) -> None:
        if len(self.stations) <= 1:
            raise ValueError("at least one station is required")
        entity = self.stations.get(station_id)
        if entity is None:
            raise ValueError("station not found")
        if entity.runner and entity.runner.is_running():
            raise ValueError("cannot remove running station")
        self.registry.release_station(station_id)
        self.stations.pop(station_id)

    def update_station_config(self, station_id: int, config: StationConfig) -> StationConfig:
        station = self.stations.get(station_id)
        if not station:
            raise ValueError("station not found")
        if station.runner and station.runner.is_running():
            raise ValueError("cannot update config while station is running")
        config.stationId = station_id
        station.config = config
        return station.config

    def get_mapping(self, station_id: int) -> StationIoMapping:
        station = self.stations.get(station_id)
        if not station:
            raise ValueError("station not found")
        return station.mapping

    def validate_mapping(self, station_id: int, mapping: StationIoMapping) -> ValidateMappingResponse:
        issues: List[ValidationIssue] = []
        required = set(LogicalSignal)
        present = set(mapping.bindings.keys())
        missing = required.difference(present)
        for sig in sorted(missing, key=lambda x: x.value):
            issues.append(ValidationIssue(level="error", message=f"Missing binding for {sig.value}"))

        expected_direction = {
            LogicalSignal.P_SENSOR: Direction.IN,
        }
        for sig, expected in expected_direction.items():
            if sig in mapping.bindings and mapping.bindings[sig].direction != expected:
                issues.append(ValidationIssue(level="error", message=f"{sig.value} must use direction={expected.value}"))

        seen: Dict[tuple[str, str, int], LogicalSignal] = {}
        for sig, ref in mapping.bindings.items():
            key = (ref.device, ref.moduleType.value if hasattr(ref.moduleType, "value") else str(ref.moduleType), ref.channel)
            if key in seen:
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=(
                            f"Channel conflict in mapping: {ref.device}:{ref.moduleType}:{ref.channel} "
                            f"for {seen[key].value} and {sig.value}"
                        ),
                    )
                )
            else:
                seen[key] = sig

        if station_id in self.stations and self.stations[station_id].runner and self.stations[station_id].runner.is_running():
            issues.append(ValidationIssue(level="warning", message="Station is running, new mapping applies to next run"))

        return ValidateMappingResponse(valid=not any(i.level == "error" for i in issues), issues=issues)

    def update_mapping(self, station_id: int, mapping: StationIoMapping) -> StationIoMapping:
        result = self.validate_mapping(station_id, mapping)
        if not result.valid:
            raise ValueError("; ".join(issue.message for issue in result.issues if issue.level == "error"))
        station = self.stations.get(station_id)
        if not station:
            raise ValueError("station not found")
        station.mapping = mapping
        self.mappings[station_id] = mapping
        self.store.save_station_overrides(self.mappings)
        return mapping

    def list_templates(self) -> List[IoTemplate]:
        return self.templates

    def upsert_template(self, template: IoTemplate) -> IoTemplate:
        idx = next((i for i, t in enumerate(self.templates) if t.templateId == template.templateId), None)
        if idx is None:
            self.templates.append(template)
        else:
            self.templates[idx] = template
        self.store.save_templates(self.templates)
        return template

    async def connect(self, station_id: int) -> None:
        station = self.stations[station_id]
        await self.driver.connect(station.config.deviceName)
        station.runtime.connected = True
        await self.bus.publish("station.status", {"status": station.runtime.status, "connected": True}, station_id)
        await self.bus.publish("station.log", {"line": "hardware connected"}, station_id)

    async def disconnect(self, station_id: int) -> None:
        station = self.stations[station_id]
        await self.driver.disconnect(station.config.deviceName)
        station.runtime.connected = False
        await self.bus.publish("station.status", {"status": station.runtime.status, "connected": False}, station_id)
        await self.bus.publish("station.log", {"line": "hardware disconnected"}, station_id)

    async def start(self, station_id: int) -> None:
        station = self.stations[station_id]
        if station.runner and station.runner.is_running():
            raise ValueError("station is already running")
        validation = self.validate_mapping(station_id, station.mapping)
        if not validation.valid:
            raise ValueError("; ".join(i.message for i in validation.issues if i.level == "error"))
        if self.system.get("simulation", False):
            station.runtime.connected = True
        self.registry.release_station(station_id)
        for ref in station.mapping.bindings.values():
            module_type = ref.moduleType.value if hasattr(ref.moduleType, "value") else str(ref.moduleType)
            conflict = self.registry.acquire(station_id, ref.device, module_type, ref.channel)
            if conflict:
                raise ValueError(conflict)
        station.runner = StationRunner(station_id, station.config, station.mapping, self.driver, self.bus, self.logger, station.runtime)
        await station.runner.start()

    async def pause(self, station_id: int) -> None:
        station = self.stations[station_id]
        if not station.runner:
            raise ValueError("station is not running")
        await station.runner.pause()

    async def resume(self, station_id: int) -> None:
        station = self.stations[station_id]
        if not station.runner:
            raise ValueError("station is not running")
        await station.runner.resume()

    async def stop(self, station_id: int) -> None:
        station = self.stations[station_id]
        if not station.runner:
            return
        await station.runner.stop()
        self.registry.release_station(station_id)

    async def debug_set_output(self, station_id: int, signal: LogicalSignal, state: bool) -> None:
        station = self.stations[station_id]
        await self.driver.set_outputs({signal: state}, station.mapping.bindings)
        await self.bus.publish("station.log", {"line": f"debug io toggle {signal.value}: {'ON' if state else 'OFF'}"}, station_id)

    async def debug_force_status(self, station_id: int, status: StationStatus) -> None:
        station = self.stations[station_id]
        station.runtime.status = status
        if status == StationStatus.ERROR:
            station.runtime.fault = "Forced alarm from debug panel"
            await self.driver.set_outputs({LogicalSignal.BUZZER: True}, station.mapping.bindings)
        await self.bus.publish("station.status", {"status": station.runtime.status, "fault": station.runtime.fault}, station_id)

    def set_log_dir(self, log_dir: str) -> None:
        clean = (log_dir or "").strip()
        if not clean:
            raise ValueError("log_dir cannot be empty")
        self.system["log_dir"] = clean
        self.logger = CsvLogger(self.root_dir / clean)
        self.store.save_system(self.system)
