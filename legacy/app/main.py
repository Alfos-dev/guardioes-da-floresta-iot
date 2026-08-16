import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

app = FastAPI()

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

class SensorPayload(BaseModel):
    device_id: str
    seq: int | None = None
    t: float | None = None
    ha: float | None = None
    s: int | None = None
    soil_raw: int | None = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ingest")
def ingest(payload: SensorPayload):
    try:
        p = Point("sensor_data").tag("device_id", payload.device_id)

        if payload.seq is not None:
            p.field("seq", payload.seq)
        if payload.t is not None:
            p.field("t", payload.t)
        if payload.ha is not None:
            p.field("ha", payload.ha)
        if payload.s is not None:
            p.field("s", payload.s)
        if payload.soil_raw is not None:
            p.field("soil_raw", payload.soil_raw)

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        return {"status": "stored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
