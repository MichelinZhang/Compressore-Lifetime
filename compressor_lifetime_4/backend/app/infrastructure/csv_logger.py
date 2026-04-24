from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


class CsvLogger:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def build_files(self, station_id: int, device: str) -> tuple[Path, Path]:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        csv_path = self.base_dir / f"Log_{device}_St{station_id}_{ts}.csv"
        meta_path = self.base_dir / f"Log_{device}_St{station_id}_{ts}.json"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Date", "Time", "Cycle", "Phase", "Step", "End_P", "Max_P", "Min_P"])
        return csv_path, meta_path

    def append_row(self, csv_path: Path, cycle: int, phase: str, step: str, end_p: float, max_p: float, min_p: float) -> None:
        now = datetime.now()
        with csv_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    cycle,
                    phase,
                    step,
                    f"{end_p:.2f}",
                    f"{max_p:.2f}",
                    f"{min_p:.2f}",
                ]
            )

    def write_meta(self, meta_path: Path, payload: dict) -> None:
        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

