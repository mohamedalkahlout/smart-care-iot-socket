"""
Telemetry Logger Module
Smart Care IoT Socket (Retrofit Edge-AI & Safety Guard)

Handles append-only telemetry storage, batching, structured JSONL & CSV logging,
and querying for operational metrics and audits.
"""
import csv
import io
import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TelemetryRecord:
    ts: int
    device_id: str
    device_type: str
    temp_c: float
    humidity_pct: float
    relay_cmd: str
    relay_actual: str
    mode: str
    source: str
    power_w: float
    rssi: int
    fw_version: str
    guard_reason: str


class TelemetryLogger:
    def __init__(self, max_buffer_size: int = 1000, log_file: Optional[str] = None):
        self.max_buffer_size = max_buffer_size
        self.log_file = log_file
        self.records: List[TelemetryRecord] = []

    def log(self, record: TelemetryRecord) -> None:
        """Stores a TelemetryRecord in memory and appends to structured log if configured."""
        self.records.append(record)
        if len(self.records) > self.max_buffer_size:
            self.records.pop(0)

        if self.log_file:
            self._append_to_file(record)

    def ingest_dict(self, data: Dict[str, Any]) -> TelemetryRecord:
        """Ingests raw dictionary from sensor or HTTP payload, converts to TelemetryRecord."""
        record = TelemetryRecord(
            ts=int(data.get("ts", time.time())),
            device_id=str(data.get("device_id", "socket1")),
            device_type=str(data.get("device_type", "cooling")),
            temp_c=float(data.get("temp_c", 0.0)),
            humidity_pct=float(data.get("humidity_pct", 0.0)),
            relay_cmd=str(data.get("relay_cmd", "off")),
            relay_actual=str(data.get("relay_actual", "off")),
            mode=str(data.get("mode", "auto")),
            source=str(data.get("source", "auto_rule")),
            power_w=float(data.get("power_w", 0.0)),
            rssi=int(data.get("rssi", -60)),
            fw_version=str(data.get("fw_version", "1.0.0")),
            guard_reason=str(data.get("guard_reason", "ALLOWED")),
        )
        self.log(record)
        return record

    def _append_to_file(self, record: TelemetryRecord) -> None:
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[TelemetryLogger] Failed to write log: {e}")

    def query_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent N records as dictionaries."""
        return [asdict(r) for r in self.records[-limit:]]

    def export_csv(self, filepath: Optional[str] = None) -> str:
        fieldnames = [
            "ts", "device_id", "device_type", "temp_c", "humidity_pct",
            "relay_cmd", "relay_actual", "mode", "source", "power_w",
            "rssi", "fw_version", "guard_reason"
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in self.records:
            writer.writerow(asdict(r))

        content = output.getvalue()
        if filepath:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                f.write(content)
        return content

    def export_jsonl(self, filepath: str) -> None:
        """Exports all records to a structured JSON Lines file."""
        with open(filepath, "w", encoding="utf-8") as f:
            for r in self.records:
                f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    def count(self) -> int:
        return len(self.records)
