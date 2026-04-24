from __future__ import annotations

import statistics
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

try:
    import nidaqmx
    from nidaqmx.constants import LineGrouping, TerminalConfiguration
except Exception:  # pragma: no cover - runtime environment may not have NI stack.
    nidaqmx = None
    LineGrouping = None
    TerminalConfiguration = None


class NiDaqDriver(AoIoDriver):
    async def connect(self, device: str) -> None:
        if nidaqmx is None:
            raise RuntimeError("nidaqmx is not installed")
        with nidaqmx.Task() as task:
            task.do_channels.add_do_chan(f"{device}/port0/line0:0", line_grouping=LineGrouping.CHAN_PER_LINE)

    async def disconnect(self, device: str) -> None:
        return None

    async def set_outputs(self, states: Dict[LogicalSignal, bool], refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        if nidaqmx is None:
            raise RuntimeError("nidaqmx is not installed")
        grouped: Dict[str, Dict[int, bool]] = {}
        for signal, state in states.items():
            ref = refs.get(signal)
            if ref is None or ref.moduleType != ModuleType.DO:
                continue
            grouped.setdefault(ref.device, {})
            grouped[ref.device][ref.channel] = (not state) if ref.invert else state

        for device, line_map in grouped.items():
            max_line = max(line_map)
            values = [line_map.get(i, False) for i in range(max_line + 1)]
            with nidaqmx.Task() as task:
                task.do_channels.add_do_chan(f"{device}/port0/line0:{max_line}", line_grouping=LineGrouping.CHAN_PER_LINE)
                task.write(values, auto_start=True)

    async def read_pressure(self, ref: PhysicalChannelRef) -> float:
        if nidaqmx is None:
            raise RuntimeError("nidaqmx is not installed")
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                f"{ref.device}/ai{ref.channel}",
                terminal_config=TerminalConfiguration.RSE,
                min_val=-10.0,
                max_val=10.0,
            )
            data = task.read(number_of_samples_per_channel=10)
        current_volts = statistics.median(data) if isinstance(data, list) else float(data)
        pressure = max(0.0, (current_volts - 1.0) * 2.5)
        return pressure

    async def read_temperature(self, ref: PhysicalChannelRef) -> float:
        return 25.0
    async def emergency_shutdown(self, refs: Dict[LogicalSignal, PhysicalChannelRef]) -> None:
        safe_off = {k: False for k in refs.keys()}
        await self.set_outputs(safe_off, refs)

    async def get_capabilities(self, device: str) -> HardwareCapabilities:
        return HardwareCapabilities(
            device=device,
            supports=["nidaqmx"],
            details=[
                HardwareChannel(moduleType=ModuleType.DO, direction=Direction.OUT, channels=list(range(0, 32))),
                HardwareChannel(moduleType=ModuleType.DI, direction=Direction.IN, channels=list(range(0, 32))),
                HardwareChannel(moduleType=ModuleType.AI, direction=Direction.IN, channels=list(range(0, 8))),
                HardwareChannel(moduleType=ModuleType.AO, direction=Direction.OUT, channels=list(range(0, 4))),
            ],
        )

