import ephem
import datetime
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- CONFIGURAÇÃO ---
INFLUX_URL = "http://influxdb:8086"
TOKEN = "meu-token-influx"
ORG = "ads"
BUCKET = "monitoramento"

client = InfluxDBClient(url=INFLUX_URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

def get_moon_phase_name(phase_percent):
    if 0 <= phase_percent < 0.03 or 0.97 <= phase_percent <= 1: return "Lua Nova"
    elif 0.03 <= phase_percent < 0.22: return "Lua Crescente"
    elif 0.22 <= phase_percent < 0.35: return "Quarto Crescente"
    elif 0.35 <= phase_percent < 0.45: return "Gibosa Crescente"
    elif 0.45 <= phase_percent < 0.55: return "Lua Cheia"
    elif 0.55 <= phase_percent < 0.65: return "Gibosa Minguante"
    elif 0.65 <= phase_percent < 0.78: return "Quarto Minguante"
    else: return "Lua Minguante"

def update_moon_data():
    print("Serviço de Lua Iniciado...")
    while True:
        try:
            now = datetime.datetime.now()
            m = ephem.Moon(now)
            illumination = m.moon_phase * 100
            phase_percent = (now.day % 29.53) / 29.53
            phase_name = get_moon_phase_name(phase_percent)
            
            point = Point("moon_data") \
                .tag("location", "Xingu") \
                .field("illumination", float(illumination)) \
                .field("phase", str(phase_name)) \
                .time(datetime.datetime.utcnow())

            write_api.write(bucket=BUCKET, record=point)
            print(f"[{now}] Inviado: {phase_name}")
        except Exception as e:
            print(f"Erro: {e}")
        time.sleep(3600)

if __name__ == "__main__":
    update_moon_data()
