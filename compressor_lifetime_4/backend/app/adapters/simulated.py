from __future__ import annotations

import random
from typing import Dict

from app.adapters.base import AoIoDriver
from app.domain.models import (
    Direction,
    HardwareCapabilities,
    HardwareChannel,
    LogicalSignal,
    ModuleType,
    PhysicalChannelRef,
)


class SimulatedDriver(AoIoDriver):
    """
    Keep simulation behavior aligned with backup `备用文件/compressor_lifetime.py`:
    - write outputs drives the base pressure: +0.15 / -0.3 / -0.05
    - read adds noise in [-0.05, +0.05]
    - pressure is bounded to [0, min(3.0, maxP)]
    """

    def __init__(self) -> None:
        self._pressure = 0.0
        self._runtime_limit = 3.0

    def set_runtime_limit(self, max_pressure: float) -> None:
        self._runtime_limit = max(0.1, min(3.0, float(max_pressure)))

    async def connect(self, device: str) -> None:
        return None

    async def disconnect(self, device: str) -> None:
        return None

    async def set_outputs(self, states: Dict[LogicalSignal, bool], refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        compressor_on = states.get(LogicalSignal.COMPRESSOR, False)
        v1 = states.get(LogicalSignal.V1, False)
        v2 = states.get(LogicalSignal.V2, False)
        v3 = states.get(LogicalSignal.V3, False)

        if compressor_on and v1:
            self._pressure += 0.15
        elif v2 or v3:
            self._pressure -= 0.3
        elif v1:
            self._pressure -= 0.05

        self._pressure = max(0.0, min(self._runtime_limit, self._pressure))

    async def read_pressure(self, ref: PhysicalChannelRef) -> float:
        noise = random.uniform(-0.05, 0.05)
        return max(0.0, min(self._runtime_limit, self._pressure + noise))

    async def read_temperature(self, ref: PhysicalChannelRef) -> float:
        return 25.0

    async def emergency_shutdown(self, refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        self._pressure = max(0.0, self._pressure - 0.5)

    async def get_capabilities(self, device: str) -> HardwareCapabilities:
        return HardwareCapabilities(
            device=device,
            supports=["simulation"],
            details=[
                HardwareChannel(moduleType=ModuleType.DO, direction=Direction.OUT, channels=list(range(0, 32))),
                HardwareChannel(moduleType=ModuleType.AI, direction=Direction.IN, channels=list(range(0, 8))),
            ],
        )
