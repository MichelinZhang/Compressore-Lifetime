from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from app.domain.models import HardwareCapabilities, LogicalSignal, PhysicalChannelRef


class AoIoDriver(ABC):
    @abstractmethod
    async def connect(self, device: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self, device: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def set_outputs(self, states: Dict[LogicalSignal, bool], refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read_pressure(self, ref: PhysicalChannelRef) -> float:
        raise NotImplementedError

    @abstractmethod
    async def read_temperature(self, ref: PhysicalChannelRef) -> float:
        raise NotImplementedError

    @abstractmethod
    async def emergency_shutdown(self, refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_capabilities(self, device: str) -> HardwareCapabilities:
        raise NotImplementedError

