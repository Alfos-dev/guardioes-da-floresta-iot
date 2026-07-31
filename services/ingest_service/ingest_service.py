"""ingest_service - the single ingestion point of the v2 architecture.

Subscribes to the MQTT broker, validates/normalizes the generic telemetry
schema, writes each reading to InfluxDB and keeps the SQLite device registry
up to date (auto-discovering unknown devices).

Topics:
    guardioes/+/telemetry  -> readings written to InfluxDB
    guardioes/+/status     -> heartbeat, updates ultimo_contato

Everything is configured through environment variables (no secrets in code).
"""
from __future__ import annotations

import json
import os
import sys
import time

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from db import DeviceRegistry
from schema import SchemaError, extract_sensor_names, validate_telemetry

# ---- MQTT config ----
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
MQTT_TELEMETRY_TOPIC = os.getenv("MQTT_TELEMETRY_TOPIC", "guardioes/+/telemetry")
MQTT_STATUS_TOPIC = os.getenv("MQTT_STATUS_TOPIC", "guardioes/+/status")

# ---- InfluxDB config ----
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "meu-token-influx")
INFLUX_ORG = os.getenv("INFLUX_ORG", "ads")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "monitoramento")

# ---- SQLite config ----
SQLITE_PATH = os.getenv("SQLITE_PATH", "/data/devices.db")


def log(msg: str) -> None:
    print(f"[ingest] {msg}", flush=True)


class IngestService:
    def __init__(self) -> None:
        self.registry = DeviceRegistry(SQLITE_PATH)
        self.influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        self.write_api = self.influx.write_api(write_options=SYNCHRONOUS)

        # paho-mqtt 2.x callback API.
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="ingest_service",
        )
        if MQTT_USER:
            self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    # -- MQTT callbacks --
    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            log(f"falha ao conectar no broker (rc={reason_code})")
            return
        log(f"conectado ao broker {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(MQTT_TELEMETRY_TOPIC, qos=1)
        client.subscribe(MQTT_STATUS_TOPIC, qos=1)
        log(f"assinando '{MQTT_TELEMETRY_TOPIC}' e '{MQTT_STATUS_TOPIC}'")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8", errors="ignore"))
        except (ValueError, UnicodeDecodeError) as exc:
            log(f"[erro json] {topic}: {exc}")
            return

        if topic.endswith("/telemetry"):
            self.handle_telemetry(topic, payload)
        elif topic.endswith("/status"):
            self.handle_status(topic, payload)

    # -- Handlers --
    def handle_telemetry(self, topic: str, payload) -> None:
        try:
            data = validate_telemetry(payload)
        except SchemaError as exc:
            log(f"[schema invalido] {topic}: {exc}")
            return

        device_id = data["device_id"]
        ts = data["timestamp"]
        readings = data["readings"]

        # Write each reading as its own point (measurement=sensor_data,
        # tags device_id + sensor, field value). Dynamic sensors need no
        # backend change (RF09).
        points = []
        for r in readings:
            points.append(
                Point("sensor_data")
                .tag("device_id", device_id)
                .tag("sensor", r["sensor"])
                .tag("unit", r["unit"])
                .field("value", r["value"])
                .time(ts)
            )
        try:
            self.write_api.write(bucket=INFLUX_BUCKET, record=points)
        except Exception as exc:  # noqa: BLE001 - keep the service alive
            log(f"[influx erro] {device_id}: {exc}")
            return

        created = self.registry.upsert_contact(
            device_id, sensors=extract_sensor_names(readings), transport="mqtt"
        )
        tag = "novo dispositivo" if created else "ok"
        log(f"[{tag}] {device_id} <- {len(readings)} readings")

    def handle_status(self, topic: str, payload) -> None:
        # topic: guardioes/{device_id}/status
        parts = topic.split("/")
        device_id = parts[1] if len(parts) >= 3 else None
        if not device_id:
            return
        online = bool(payload.get("online", True)) if isinstance(payload, dict) else True
        self.registry.touch_status(device_id)
        log(f"[status] {device_id} online={online}")

    def run(self) -> None:
        # Retry loop so the service survives the broker not being up yet.
        while True:
            try:
                log(f"conectando ao broker {MQTT_HOST}:{MQTT_PORT} ...")
                self.client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
                break
            except Exception as exc:  # noqa: BLE001
                log(f"broker indisponivel ({exc}); tentando novamente em 3s")
                time.sleep(3)
        self.client.loop_forever()


def main() -> int:
    svc = IngestService()
    try:
        svc.run()
    except KeyboardInterrupt:
        log("encerrando")
        return 0


if __name__ == "__main__":
    sys.exit(main())
