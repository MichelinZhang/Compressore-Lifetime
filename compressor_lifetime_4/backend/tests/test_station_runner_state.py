from __future__ import annotations

import asyncio
from pathlib import Path

from app.adapters.simulated import SimulatedDriver
from app.application.station_manager import StationManager
from app.infrastructure.config_store import ConfigStore
from app.infrastructure.event_bus import EventBus


def build_manager(tmp_path: Path) -> StationManager:
    store = ConfigStore(tmp_path / "config")
    bus = EventBus()
    manager = StationManager(store=store, bus=bus, root_dir=tmp_path)
    manager.system["simulation"] = True
    manager.driver = SimulatedDriver()
    return manager


def test_start_reentry_is_blocked(tmp_path: Path) -> None:
    async def scenario() -> None:
        manager = build_manager(tmp_path)
        await manager.start(1)
        try:
            await manager.start(1)
            assert False, "second start must fail while station is running"
        except ValueError as exc:
            assert "already running" in str(exc)
        await manager.stop(1)

    asyncio.run(scenario())
