"""SQLite access for the device registry.

InfluxDB stores the time series; SQLite stores the mutable device metadata
(name, board, transport, sensors, calibration, last-seen). This is what feeds
the admin panel and satisfies RF12/RF13/RNF10.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

DEFAULT_DB_PATH = os.getenv("SQLITE_PATH", "/data/devices.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
  device_id      TEXT PRIMARY KEY,
  nome           TEXT,
  placa          TEXT DEFAULT 'ESP32-S3',
  transporte     TEXT DEFAULT 'mqtt',
  sensores       TEXT,          -- JSON array
  calibracao     TEXT,          -- JSON object
  ultimo_contato TEXT,
  criado_em      TEXT
);
"""


class DeviceRegistry:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def upsert_contact(
        self,
        device_id: str,
        sensors: Optional[list[str]] = None,
        transport: str = "mqtt",
    ) -> bool:
        """Updates ultimo_contato for a device, creating it on first sight.

        Returns True when a new device was auto-discovered.
        """
        now = self._now_iso()
        cur = self._conn.cursor()
        cur.execute("SELECT device_id, sensores FROM devices WHERE device_id = ?", (device_id,))
        row = cur.fetchone()

        created = False
        if row is None:
            # Auto-discovery: register unknown devices automatically.
            cur.execute(
                """INSERT INTO devices
                   (device_id, nome, placa, transporte, sensores, calibracao, ultimo_contato, criado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    device_id,
                    device_id,               # default name = id
                    "ESP32-S3",
                    transport,
                    json.dumps(sensors or []),
                    json.dumps({}),
                    now,
                    now,
                ),
            )
            created = True
        else:
            # Merge any newly seen sensor names into the stored list.
            merged = None
            if sensors:
                try:
                    existing = json.loads(row["sensores"] or "[]")
                except (TypeError, ValueError):
                    existing = []
                merged = list(existing)
                for s in sensors:
                    if s not in merged:
                        merged.append(s)
            if merged is not None:
                cur.execute(
                    "UPDATE devices SET ultimo_contato = ?, sensores = ? WHERE device_id = ?",
                    (now, json.dumps(merged), device_id),
                )
            else:
                cur.execute(
                    "UPDATE devices SET ultimo_contato = ? WHERE device_id = ?",
                    (now, device_id),
                )
        self._conn.commit()
        return created

    def touch_status(self, device_id: str) -> None:
        """Updates only ultimo_contato from a status/heartbeat message."""
        now = self._now_iso()
        cur = self._conn.cursor()
        cur.execute("SELECT 1 FROM devices WHERE device_id = ?", (device_id,))
        if cur.fetchone() is None:
            self.upsert_contact(device_id)
            return
        cur.execute(
            "UPDATE devices SET ultimo_contato = ? WHERE device_id = ?",
            (now, device_id),
        )
        self._conn.commit()

    def get(self, device_id: str) -> Optional[dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        self._conn.close()
