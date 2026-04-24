from __future__ import annotations

from typing import Dict

from app.adapters.base import AoIoDriver
from app.domain.models import HardwareCapabilities, LogicalSignal, PhysicalChannelRef


class Esp32HttpDriver(AoIoDriver):
    """
    Placeholder adapter for future ESP32 migration.
    Contract shape matches NI adapter, business layer remains unchanged.
    """

    async def connect(self, device: str) -> None:
        raise NotImplementedError("ESP32 adapter is reserved for future implementation")

    async def disconnect(self, device: str) -> None:
        raise NotImplementedError("ESP32 adapter is reserved for future implementation")

    async def set_outputs(self, states: Dict[LogicalSignal, bool], refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        raise NotImplementedError("ESP32 adapter is reserved for future implementation")

    async def read_pressure(self, ref: PhysicalChannelRef) -> float:
        raise NotImplementedError("ESP32 adapter is reserved for future implementation")

    async def read_temperature(self, ref: PhysicalChannelRef) -> float:
        raise NotImplementedError("ESP32 adapter is reserved for future implementation")

    async def emergency_shutdown(self, refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        raise NotImplementedError("ESP32 adapter is reserved for future implementation")

    async def get_capabilities(self, device: str) -> HardwareCapabilities:
        raise NotImplementedError("ESP32 adapter is reserved for future implementation")
