from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from day0_boot_sim.models import DeviceRecord, TimelineEvent


class Storage:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

    def initialize(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    serial TEXT,
                    model TEXT,
                    management_ip TEXT,
                    dhcp_server_ip TEXT,
                    boot_file_uri TEXT,
                    config_server_uri TEXT,
                    bootstrap_checksum TEXT,
                    last_error TEXT,
                    ready INTEGER NOT NULL,
                    last_boot_at TEXT
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                )
                """
            )
            self._connection.commit()

    def health(self) -> bool:
        with self._lock:
            self._connection.execute("SELECT 1")
        return True

    def upsert_device(self, record: DeviceRecord) -> DeviceRecord:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO devices (
                    device_id, state, scenario, operator, serial, model,
                    management_ip, dhcp_server_ip, boot_file_uri, config_server_uri,
                    bootstrap_checksum, last_error, ready, last_boot_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    state = excluded.state,
                    scenario = excluded.scenario,
                    operator = excluded.operator,
                    serial = excluded.serial,
                    model = excluded.model,
                    management_ip = excluded.management_ip,
                    dhcp_server_ip = excluded.dhcp_server_ip,
                    boot_file_uri = excluded.boot_file_uri,
                    config_server_uri = excluded.config_server_uri,
                    bootstrap_checksum = excluded.bootstrap_checksum,
                    last_error = excluded.last_error,
                    ready = excluded.ready,
                    last_boot_at = excluded.last_boot_at
                """,
                (
                    record.device_id,
                    record.state.value,
                    record.scenario.value,
                    record.operator,
                    record.serial,
                    record.model,
                    record.management_ip,
                    record.dhcp_server_ip,
                    record.boot_file_uri,
                    record.config_server_uri,
                    record.bootstrap_checksum,
                    record.last_error,
                    int(record.ready),
                    record.last_boot_at.isoformat() if record.last_boot_at else None,
                ),
            )
            self._connection.commit()
        return self.get_device(record.device_id) or record

    def get_device(self, device_id: str) -> DeviceRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        if row is None:
            return None
        return self._device_from_row(row)

    def list_devices(self) -> list[DeviceRecord]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM devices ORDER BY device_id").fetchall()
        return [self._device_from_row(row) for row in rows]

    def add_timeline_event(
        self,
        device_id: str,
        state: str,
        event_type: str,
        message: str,
        details: dict[str, object],
        occurred_at: datetime,
    ) -> TimelineEvent:
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO timeline (device_id, state, event_type, message, details_json, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (device_id, state, event_type, message, json.dumps(details), occurred_at.isoformat()),
            )
            self._connection.commit()
            event_id = int(cursor.lastrowid)
        return TimelineEvent(
            id=event_id,
            device_id=device_id,
            state=state,
            event_type=event_type,
            message=message,
            details=details,
            occurred_at=occurred_at,
        )

    def get_timeline(self, device_id: str) -> list[TimelineEvent]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM timeline WHERE device_id = ? ORDER BY id",
                (device_id,),
            ).fetchall()
        return [self._timeline_from_row(row) for row in rows]

    @staticmethod
    def _device_from_row(row: sqlite3.Row) -> DeviceRecord:
        return DeviceRecord.model_validate(
            {
                "device_id": row["device_id"],
                "state": row["state"],
                "scenario": row["scenario"],
                "operator": row["operator"],
                "serial": row["serial"],
                "model": row["model"],
                "management_ip": row["management_ip"],
                "dhcp_server_ip": row["dhcp_server_ip"],
                "boot_file_uri": row["boot_file_uri"],
                "config_server_uri": row["config_server_uri"],
                "bootstrap_checksum": row["bootstrap_checksum"],
                "last_error": row["last_error"],
                "ready": bool(row["ready"]),
                "last_boot_at": row["last_boot_at"],
            }
        )

    @staticmethod
    def _timeline_from_row(row: sqlite3.Row) -> TimelineEvent:
        return TimelineEvent.model_validate(
            {
                "id": row["id"],
                "device_id": row["device_id"],
                "state": row["state"],
                "event_type": row["event_type"],
                "message": row["message"],
                "details": json.loads(row["details_json"]),
                "occurred_at": row["occurred_at"],
            }
        )
