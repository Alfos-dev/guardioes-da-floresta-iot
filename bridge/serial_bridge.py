import os
import time
import json
import serial
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
BAUD        = int(os.getenv("BAUD", "115200"))
INFLUX_URL  = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "meu-token-influx")
INFLUX_ORG  = os.getenv("INFLUX_ORG", "ads")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "monitoramento")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

while True:
    try:
        with serial.Serial(SERIAL_PORT, BAUD, timeout=1) as ser:
            print(f"[bridge] conectado em {SERIAL_PORT}")
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    point = (
                        Point("sensor_data")
                        .tag("device_id", data.get("device_id", "esp32_1"))
                        .field("t",        float(data["t"]))
                        .field("ha",       float(data["ha"]))
                        .field("s",        float(data["s"]))
                        .field("soil_raw", int(data["soil_raw"]))
                    )
                    write_api.write(bucket=INFLUX_BUCKET, record=point)
                    print("[ok] Gravado:", data)
                except Exception as e:
                    print("[erro]", e)
    except Exception as e:
        print("[serial offline]", e)
        time.sleep(3)
