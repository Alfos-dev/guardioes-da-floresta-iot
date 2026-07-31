"""serial_bridge - serial -> MQTT adapter (v2).

In v1 this component read JSON from the serial port and wrote it straight to
InfluxDB. In v2 there is a single ingestion point (ingest_service), and every
transport funnels through MQTT first. So the bridge now simply:

    1. reads a JSON line from the serial port,
    2. converts it to the generic telemetry schema (readings[]),
    3. publishes it to guardioes/{device_id}/telemetry on the broker.

It stays backwards compatible with existing serial devices (RNF06): if the
line already uses the generic schema, it is forwarded as-is; if it uses the
legacy v1 payload (t, ha, s, soil_raw), it is converted first.

All connection settings come from environment variables (no secrets in code).
"""
import json
import os
import time

import paho.mqtt.client as mqtt
import serial

# ---- Serial config ----
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUD = int(os.getenv("BAUD", "115200"))

# ---- MQTT config ----
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
# Fallback device id when the serial payload does not carry one.
DEFAULT_DEVICE_ID = os.getenv("DEVICE_ID", "esp32s3_serial")


def log(msg: str) -> None:
    print(f"[bridge] {msg}", flush=True)


def to_generic(data: dict) -> dict | None:
    """Converts a serial payload to the generic telemetry schema.

    Returns the generic payload dict, or None if the line has nothing useful.
    """
    # Already generic? Forward as-is (ensure device_id is present).
    if isinstance(data.get("readings"), list):
        data.setdefault("device_id", DEFAULT_DEVICE_ID)
        return data

    # Legacy v1 payload: t (temp), ha (air humidity), s (soil %), soil_raw.
    device_id = data.get("device_id", DEFAULT_DEVICE_ID)
    readings = []
    if data.get("t") is not None:
        readings.append({"sensor": "air_temp", "value": float(data["t"]), "unit": "C"})
    if data.get("ha") is not None:
        readings.append({"sensor": "air_humidity", "value": float(data["ha"]), "unit": "%"})
    if data.get("s") is not None:
        readings.append({"sensor": "soil_moisture", "value": float(data["s"]), "unit": "%"})
    if data.get("soil_raw") is not None:
        readings.append({"sensor": "soil_raw", "value": float(data["soil_raw"]), "unit": "adc"})

    if not readings:
        return None
    return {"device_id": device_id, "readings": readings}


def make_client() -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="serial_bridge",
    )
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    return client


def connect_mqtt(client: mqtt.Client) -> None:
    while True:
        try:
            log(f"conectando ao broker {MQTT_HOST}:{MQTT_PORT} ...")
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_start()
            log("conectado ao broker")
            return
        except Exception as exc:  # noqa: BLE001
            log(f"broker indisponivel ({exc}); nova tentativa em 3s")
            time.sleep(3)


def main() -> None:
    client = make_client()
    connect_mqtt(client)

    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD, timeout=1) as ser:
                log(f"conectado na serial {SERIAL_PORT}")
                while True:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except ValueError:
                        # Non-JSON lines (boot/info messages) are ignored.
                        continue

                    generic = to_generic(data)
                    if generic is None:
                        continue

                    device_id = generic["device_id"]
                    topic = f"guardioes/{device_id}/telemetry"
                    client.publish(topic, json.dumps(generic), qos=1)
                    log(f"[ok] {topic} <- {len(generic['readings'])} readings")
        except serial.SerialException as exc:
            log(f"[serial offline] {exc}")
            time.sleep(3)
        except Exception as exc:  # noqa: BLE001
            log(f"[erro] {exc}")
            time.sleep(3)


if __name__ == "__main__":
    main()
