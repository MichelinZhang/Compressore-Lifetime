from __future__ import annotations

from typing import Dict, Optional, Tuple


class ChannelRegistry:
    def __init__(self) -> None:
        self._owners: Dict[Tuple[str, str, int], int] = {}

    def acquire(self, station_id: int, device: str, module_type: str, channel: int) -> Optional[str]:
        key = (device, module_type, channel)
        owner = self._owners.get(key)
        if owner is not None and owner != station_id:
            return f"Channel conflict on {device}:{module_type}:{channel} (owned by station {owner})"
        self._owners[key] = station_id
        return None

    def release_station(self, station_id: int) -> None:
        remove_keys = [k for k, owner in self._owners.items() if owner == station_id]
        for key in remove_keys:
            self._owners.pop(key, None)
