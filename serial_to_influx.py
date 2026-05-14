import serial
import json
import time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Configurações
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "meu-token-influx"
INFLUX_ORG = "ads"
INFLUX_BUCKET = "monitoramento"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("Iniciando leitura da serial...")

with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5) as ser:
    while True:
        try:
            line = ser.readline().decode("utf-8").strip()
            if not line:
                continue

            data = json.loads(line)
            print(f"Recebido: {data}")

            point = (
                Point("sensor_data")
                .tag("device_id", data.get("device_id", "esp32_1"))
                .field("t",  float(data["t"]))
                .field("ha", float(data["ha"]))
                .field("s",  float(data["s"]))
                .field("soil_raw", int(data["soil_raw"]))
            )

            write_api.write(bucket=INFLUX_BUCKET, record=point)
            print("✓ Gravado no InfluxDB")

        except json.JSONDecodeError:
            print(f"Linha ignorada (não é JSON): {line}")
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(2)
