# -*- coding: utf-8 -*-
"""Per-device DAQ resource pool: one shared multi-channel AI task, per-group DO tasks."""

from __future__ import annotations

import threading
import time
import statistics
from collections import deque

import nidaqmx
from nidaqmx.constants import LineGrouping, TerminalConfiguration, AcquisitionType

AI_SAMPLE_RATE = 500
AI_BUFFER_SAMPLES = 1000
AI_READER_INTERVAL_S = 0.02
PRESSURE_DEQUE_LEN = 4
DEFAULT_AI_CHANNEL_COUNT = 6


def _build_do_lines(dev_name: str, group_cfg: dict) -> str:
    return (
        f"{dev_name}/port{group_cfg['port']}/"
        f"line{group_cfg['line_start']}:{group_cfg['line_end']}"
    )


def _volts_to_pressure(volts: float) -> float:
    return max(0.0, (volts - 1.0) * 2.5)


class AiReaderThread(threading.Thread):
    def __init__(self, manager: "DaqDeviceManager"):
        super().__init__(daemon=True, name=f"AiReader-{manager.dev_name}")
        self._manager = manager
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            try:
                self._manager._poll_ai_once()
            except Exception:
                pass
            self._stop.wait(AI_READER_INTERVAL_S)

    def stop(self):
        self._stop.set()


class DaqDeviceManager:
    """One Dev1: shared ai0..aiN continuous task + one DO task per group_id."""

    def __init__(self, dev_name: str, ai_channel_count: int = DEFAULT_AI_CHANNEL_COUNT):
        self.dev_name = dev_name.strip()
        self._ai_channel_count = ai_channel_count
        self._lock = threading.RLock()
        self._ai_task = None
        self._ai_reader: AiReaderThread | None = None
        self._ai_owners: set[str] = set()
        self._filter_deques: dict[int, deque] = {}
        self._pressure_cache: dict[int, float] = {}
        self._raw_cache: dict[int, float] = {}
        self._do_tasks: dict[int, object] = {}
        self._do_owners: dict[int, str] = {}

    def is_group_busy(self, group_id: int, exclude_owner: str | None = None) -> bool:
        with self._lock:
            owner = self._do_owners.get(int(group_id))
            if owner is None:
                return False
            if exclude_owner and owner == exclude_owner:
                return False
            return True

    def get_group_busy_message(self, group_id: int) -> str | None:
        with self._lock:
            owner = self._do_owners.get(int(group_id))
            if owner is None:
                return None
            if owner.startswith("debug"):
                kind = "调试模式"
            elif owner.startswith("worker"):
                kind = "测试任务"
            else:
                kind = "其他任务"
            return f"Group {group_id} 正被{kind}占用"

    def acquire_do(self, group_cfg: dict, owner: str):
        group_id = int(group_cfg["group_id"])
        with self._lock:
            existing = self._do_owners.get(group_id)
            if existing is not None and existing != owner:
                raise RuntimeError(f"Group {group_id} 已被占用 ({existing})")
            if group_id in self._do_tasks:
                return self._do_tasks[group_id]

            task = nidaqmx.Task()
            try:
                lines = _build_do_lines(self.dev_name, group_cfg)
                task.do_channels.add_do_chan(lines, line_grouping=LineGrouping.CHAN_PER_LINE)
                task.start()
                task.write([False] * 8)
            except Exception as e:
                try:
                    task.close()
                except Exception:
                    pass
                raise RuntimeError(f"DO初始化失败: {e}") from e

            self._do_tasks[group_id] = task
            self._do_owners[group_id] = owner
            return task

    def release_do(self, group_id: int, owner: str) -> None:
        with self._lock:
            if self._do_owners.get(group_id) != owner:
                return
            task = self._do_tasks.pop(group_id, None)
            self._do_owners.pop(group_id, None)
        if task is not None:
            self._safe_close_do_task(task, write_safe=False)

    def acquire_ai(self, ai_channel: int, owner: str) -> None:
        ai_channel = int(ai_channel)
        if ai_channel < 0 or ai_channel >= self._ai_channel_count:
            raise ValueError(f"AI 通道超出范围: ai{ai_channel}")

        with self._lock:
            if owner in self._ai_owners:
                return
            self._filter_deques.setdefault(ai_channel, deque(maxlen=PRESSURE_DEQUE_LEN))
            self._ai_owners.add(owner)
            if len(self._ai_owners) == 1:
                try:
                    self._start_ai_task()
                except Exception:
                    self._ai_owners.discard(owner)
                    raise

    def release_ai(self, owner: str) -> None:
        with self._lock:
            self._ai_owners.discard(owner)
            if self._ai_owners:
                return
        self._stop_ai_task()

    def read_pressure(self, ai_channel: int) -> float:
        ai_channel = int(ai_channel)
        with self._lock:
            return float(self._pressure_cache.get(ai_channel, 0.0))

    def read_pressure_snapshot(self) -> dict[int, float]:
        """一次加锁读取全部 AI 通道缓存，供多工位 UI 批量刷新。"""
        with self._lock:
            return {ch: float(val) for ch, val in self._pressure_cache.items()}

    def read_pressure_raw(self, ai_channel: int) -> float:
        ai_channel = int(ai_channel)
        with self._lock:
            return float(self._raw_cache.get(ai_channel, 0.0))

    def shutdown(self) -> None:
        with self._lock:
            group_ids = list(self._do_tasks.keys())
            self._do_owners.clear()
        for group_id in group_ids:
            with self._lock:
                task = self._do_tasks.pop(group_id, None)
            if task is not None:
                self._safe_close_do_task(task, write_safe=True)
        self._stop_ai_task()
        with self._lock:
            self._ai_owners.clear()
            self._pressure_cache.clear()
            self._raw_cache.clear()
            self._filter_deques.clear()

    def _start_ai_task(self) -> None:
        if self._ai_task is not None:
            return
        last = self._ai_channel_count - 1
        chan_spec = f"{self.dev_name}/ai0:{last}"
        task = nidaqmx.Task()
        try:
            task.ai_channels.add_ai_voltage_chan(
                chan_spec,
                terminal_config=TerminalConfiguration.RSE,
                min_val=-10.0,
                max_val=10.0,
            )
            task.timing.cfg_samp_clk_timing(
                rate=AI_SAMPLE_RATE,
                sample_mode=AcquisitionType.CONTINUOUS,
                samps_per_chan=AI_BUFFER_SAMPLES,
            )
            task.start()
        except Exception as e:
            try:
                task.close()
            except Exception:
                pass
            self._ai_owners.clear()
            raise RuntimeError(f"AI初始化失败: {e}") from e

        self._ai_task = task
        for ch in range(self._ai_channel_count):
            self._filter_deques.setdefault(ch, deque(maxlen=PRESSURE_DEQUE_LEN))
            self._pressure_cache.setdefault(ch, 0.0)
            self._raw_cache.setdefault(ch, 0.0)

        reader = AiReaderThread(self)
        self._ai_reader = reader
        reader.start()

    def _stop_ai_task(self) -> None:
        reader = self._ai_reader
        self._ai_reader = None
        if reader is not None:
            reader.stop()
            reader.join(timeout=2.0)

        task = self._ai_task
        self._ai_task = None
        if task is None:
            return
        try:
            task.stop()
        except Exception:
            pass
        try:
            task.close()
        except Exception:
            pass

    def _poll_ai_once(self) -> None:
        with self._lock:
            task = self._ai_task
            if task is None:
                return

        data = task.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)

        if not data:
            return

        # Single channel: flat list; multi channel: list of lists (one list per aiN).
        if self._ai_channel_count == 1:
            channel_batches = [data]
        elif isinstance(data[0], (list, tuple)):
            channel_batches = data
        else:
            channel_batches = [data]

        with self._lock:
            for ch, samples in enumerate(channel_batches):
                if ch >= self._ai_channel_count or not samples:
                    continue
                raw_volts = float(samples[-1])
                self._raw_cache[ch] = _volts_to_pressure(raw_volts)

                if len(samples) >= 3:
                    median_volts = statistics.median(samples)
                else:
                    median_volts = float(samples[0])

                mid_p = _volts_to_pressure(median_volts)
                dq = self._filter_deques.setdefault(ch, deque(maxlen=PRESSURE_DEQUE_LEN))
                dq.append(mid_p)
                filtered_p = sum(dq) / len(dq)
                if filtered_p < 0.015:
                    filtered_p = 0.0
                self._pressure_cache[ch] = filtered_p

    @staticmethod
    def _safe_close_do_task(task, write_safe: bool) -> None:
        if write_safe:
            try:
                task.write([False] * 8)
            except Exception:
                pass
        try:
            task.stop()
        except Exception:
            pass
        try:
            task.close()
        except Exception:
            pass
