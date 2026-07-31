"""Validation of the generic telemetry payload.

The v2 architecture unifies every transport (serial and Wi-Fi) and every sensor
into one generic schema, so the backend never needs to know a sensor in
advance:

    {
      "device_id": "esp32s3_01",
      "timestamp": "2026-07-30T14:00:00Z",   # optional
      "readings": [
        { "sensor": "soil_moisture", "value": 42,   "unit": "%" },
        { "sensor": "air_temp",      "value": 27.4, "unit": "C" }
      ]
    }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SchemaError(ValueError):
    """Raised when a telemetry payload does not match the generic schema."""


def _parse_timestamp(value: Any) -> datetime:
    """Returns a timezone-aware datetime. Falls back to 'now' when absent."""
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        # Epoch seconds.
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return datetime.now(timezone.utc)
        # Accept trailing 'Z' as UTC.
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise SchemaError(f"timestamp invalido: {value!r}") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    raise SchemaError(f"timestamp de tipo invalido: {type(value).__name__}")


def validate_telemetry(payload: Any) -> dict:
    """Validates and normalizes a telemetry payload.

    Returns a dict with keys: device_id (str), timestamp (datetime),
    readings (list of {sensor, value, unit}). Raises SchemaError on any
    structural problem.
    """
    if not isinstance(payload, dict):
        raise SchemaError("payload deve ser um objeto JSON")

    device_id = payload.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip():
        raise SchemaError("campo 'device_id' ausente ou vazio")
    device_id = device_id.strip()

    timestamp = _parse_timestamp(payload.get("timestamp"))

    readings_in = payload.get("readings")
    if not isinstance(readings_in, list) or not readings_in:
        raise SchemaError("campo 'readings' ausente ou vazio")

    readings_out: list[dict] = []
    for i, item in enumerate(readings_in):
        if not isinstance(item, dict):
            raise SchemaError(f"readings[{i}] deve ser um objeto")
        sensor = item.get("sensor")
        if not isinstance(sensor, str) or not sensor.strip():
            raise SchemaError(f"readings[{i}].sensor ausente ou vazio")
        value = item.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SchemaError(f"readings[{i}].value deve ser numerico")
        unit = item.get("unit", "")
        if unit is None:
            unit = ""
        if not isinstance(unit, str):
            raise SchemaError(f"readings[{i}].unit deve ser string")
        readings_out.append(
            {"sensor": sensor.strip(), "value": float(value), "unit": unit.strip()}
        )

    return {"device_id": device_id, "timestamp": timestamp, "readings": readings_out}


def extract_sensor_names(readings: list[dict]) -> list[str]:
    """Returns the distinct sensor names present in the readings list."""
    seen: list[str] = []
    for r in readings:
        name = r.get("sensor")
        if name and name not in seen:
            seen.append(name)
    return seen
