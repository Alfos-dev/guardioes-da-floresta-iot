import ephem
import datetime
import time
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- CONFIGURAÇÃO via variáveis de ambiente ---
INFLUX_URL   = os.getenv("INFLUX_URL",    "http://influxdb:8086")
TOKEN        = os.getenv("INFLUX_TOKEN",  "meu-token-influx")
ORG          = os.getenv("INFLUX_ORG",    "ads")
BUCKET       = os.getenv("INFLUX_BUCKET", "monitoramento")

client    = InfluxDBClient(url=INFLUX_URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

def get_moon_phase_name(phase_percent):
    if   0    <= phase_percent < 0.03 or 0.97 <= phase_percent <= 1: return "Lua Nova"
    elif 0.03 <= phase_percent < 0.22: return "Lua Crescente"
    elif 0.22 <= phase_percent < 0.35: return "Quarto Crescente"
    elif 0.35 <= phase_percent < 0.45: return "Gibosa Crescente"
    elif 0.45 <= phase_percent < 0.55: return "Lua Cheia"
    elif 0.55 <= phase_percent < 0.65: return "Gibosa Minguante"
    elif 0.65 <= phase_percent < 0.78: return "Quarto Minguante"
    else:                               return "Lua Minguante"

def update_moon_data():
    print("Servico de Lua Iniciado...")
    while True:
        try:
            now       = datetime.datetime.utcnow()
            now_ephem = ephem.Date(now)
            m         = ephem.Moon(now_ephem)

            illumination = float(m.moon_phase) * 100.0

            prev_new  = ephem.previous_new_moon(now_ephem)
            age_days  = round(float(now_ephem - prev_new), 2)

            phase_percent = age_days / 29.53
            phase_name    = get_moon_phase_name(phase_percent)

            point = (
                Point("moon_data")
                .tag("location", "Xingu")
                .field("illumination", illumination)
                .field("age_days",     age_days)
                .field("phase",        phase_name)
                .time(now)
            )

            write_api.write(bucket=BUCKET, record=point)
            print(f"[{now}] {phase_name} | {illumination:.1f}% | {age_days} dias")

        except Exception as e:
            print(f"[erro] {e}")

        time.sleep(3600)

if __name__ == "__main__":
    update_moon_data()
