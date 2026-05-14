import json
import time
from datetime import datetime
from pathlib import Path
from influxdb_client import InfluxDBClient, Point

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "meu-token-influx"
INFLUX_ORG = "ads"
INFLUX_BUCKET = "monitoramento"

JSON_FILE = Path("/home/adsserver/monitoramento-iot/calendario_lunar_2026.json")

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = client.write_api()

def load_calendar():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    events = []
    for item in raw:
        dt = datetime.strptime(
            f"{item['date']} {item['time']}",
            "%Y-%m-%d %H:%M"
        )
        events.append({
            "datetime": dt,
            "date": item["date"],
            "time": item["time"],
            "phase": item["phase"]
        })

    return sorted(events, key=lambda x: x["datetime"])

def current_moon_phase(events):
    now = datetime.now()

    current = events[0]

    for event in events:
        if event["datetime"] <= now:
            current = event
        else:
            break

    return current

events = load_calendar()

while True:
    moon = current_moon_phase(events)

    point = (
        Point("moon_data")
        .field("phase", moon["phase"])
        .field("phase_date", moon["date"])
        .field("phase_time", moon["time"])
    )

    write_api.write(bucket=INFLUX_BUCKET, record=point)

    print(f"Lua atual: {moon['phase']} | desde {moon['date']} {moon['time']}")

    time.sleep(60)
