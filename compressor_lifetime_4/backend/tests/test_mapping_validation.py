from pathlib import Path

from app.application.station_manager import StationManager, default_mapping
from app.domain.models import Direction, LogicalSignal
from app.infrastructure.config_store import ConfigStore
from app.infrastructure.event_bus import EventBus


def build_manager(tmp_path: Path) -> StationManager:
    store = ConfigStore(tmp_path / "config")
    bus = EventBus()
    return StationManager(store=store, bus=bus, root_dir=tmp_path)


def test_mapping_conflict_detected(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    mapping = default_mapping(1)
    mapping.bindings[LogicalSignal.V2].channel = mapping.bindings[LogicalSignal.V1].channel
    result = manager.validate_mapping(1, mapping)
    assert result.valid is False
    assert any("conflict" in issue.message.lower() for issue in result.issues)


def test_mapping_direction_error(tmp_path: Path) -> None:
    manager = build_manager(tmp_path)
    mapping = default_mapping(1)
    mapping.bindings[LogicalSignal.P_SENSOR].direction = Direction.OUT
    result = manager.validate_mapping(1, mapping)
    assert result.valid is False
    assert any("direction" in issue.message.lower() for issue in result.issues)

