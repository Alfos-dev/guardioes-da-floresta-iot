#!/usr/bin/env python3
"""
Guardiões da Floresta IoT - Painel de Administração
Backend FastAPI para gerenciamento de dispositivos e visualização de dados
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import jwt
from passlib.hash import bcrypt
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, QueryApi

# Configurações via variáveis de ambiente
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Senha gerada pelo instalador
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# SQLite
SQLITE_PATH = os.getenv("SQLITE_PATH", "/data/devices.db")

# MQTT
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "guardioes")
MQTT_PASS = os.getenv("MQTT_PASS", "")

# InfluxDB
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_ADMIN_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUXDB_ORG", "guardioes")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "sensor_data")

# Cliente MQTT global
mqtt_client: Optional[mqtt.Client] = None
influx_client: Optional[InfluxDBClient] = None
influx_query_api: Optional[QueryApi] = None


# ===== Lifecycle Management =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação"""
    global mqtt_client, influx_client, influx_query_api
    
    # Startup: conectar MQTT e InfluxDB
    print(f"[STARTUP] Conectando ao MQTT broker {MQTT_HOST}:{MQTT_PORT}...")
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("[STARTUP] Conectado ao MQTT broker")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar MQTT: {e}")
    
    print(f"[STARTUP] Conectando ao InfluxDB {INFLUX_URL}...")
    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        influx_query_api = influx_client.query_api()
        print("[STARTUP] Conectado ao InfluxDB")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar InfluxDB: {e}")
    
    yield  # Aplicação roda
    
    # Shutdown: desconectar
    print("[SHUTDOWN] Desconectando...")
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    if influx_client:
        influx_client.close()


app = FastAPI(
    title="Guardiões da Floresta - Admin Panel",
    version="2.0.0-phase3",
    lifespan=lifespan
)

# Security
security = HTTPBearer()


# ===== Models =====
class LoginRequest(BaseModel):
    password: str


class DeviceBase(BaseModel):
    device_id: str
    nome: Optional[str] = None
    placa: str = "ESP32-S3"
    transporte: str = "mqtt"


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    nome: Optional[str] = None


class CalibrationUpdate(BaseModel):
    soil_dry: Optional[float] = None
    soil_wet: Optional[float] = None
    publish_interval: Optional[int] = None


class Device(DeviceBase):
    sensores: Optional[List[str]] = None
    calibracao: Optional[Dict[str, Any]] = None
    ultimo_contato: Optional[str] = None
    criado_em: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== Database Helper =====
def get_db():
    """Cria conexão com SQLite"""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa banco de dados se não existir"""
    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            nome TEXT,
            placa TEXT DEFAULT 'ESP32-S3',
            transporte TEXT DEFAULT 'mqtt',
            sensores TEXT,
            calibracao TEXT,
            ultimo_contato TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# ===== Auth =====
def create_token(payload: dict) -> str:
    """Cria token JWT"""
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload["exp"] = exp
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verifica token JWT"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


# ===== MQTT Helper =====
def publish_device_config(device_id: str, config: dict):
    """Publica configuração no tópico MQTT retained do dispositivo"""
    if not mqtt_client:
        raise HTTPException(status_code=503, detail="MQTT não disponível")
    
    topic = f"guardioes/{device_id}/config"
    payload = json.dumps(config)
    
    result = mqtt_client.publish(topic, payload, qos=1, retain=True)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise HTTPException(status_code=500, detail=f"Falha ao publicar config MQTT: {result.rc}")
    
    print(f"[MQTT] Publicado config para {device_id}: {payload}")


# ===== Endpoints =====
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Autentica usuário e retorna token JWT"""
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta")
    
    token = create_token({"sub": "admin"})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/devices", response_model=List[Device])
async def list_devices(auth: dict = Depends(verify_token)):
    """Lista todos os dispositivos registrados"""
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.fetchall()
    
    devices = []
    for row in cursor.execute("SELECT * FROM devices ORDER BY criado_em DESC"):
        device = dict(row)
        # Parse JSON fields
        if device.get("sensores"):
            device["sensores"] = json.loads(device["sensores"])
        if device.get("calibracao"):
            device["calibracao"] = json.loads(device["calibracao"])
        devices.append(device)
    
    conn.close()
    return devices


@app.get("/api/devices/{device_id}", response_model=Device)
async def get_device(device_id: str, auth: dict = Depends(verify_token)):
    """Obtém detalhes de um dispositivo específico"""
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    
    device = dict(row)
    if device.get("sensores"):
        device["sensores"] = json.loads(device["sensores"])
    if device.get("calibracao"):
        device["calibracao"] = json.loads(device["calibracao"])
    
    return device


@app.post("/api/devices", response_model=Device, status_code=status.HTTP_201_CREATED)
async def create_device(device: DeviceCreate, auth: dict = Depends(verify_token)):
    """Cadastra um novo dispositivo"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar se já existe
    existing = cursor.execute("SELECT device_id FROM devices WHERE device_id = ?", (device.device_id,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Dispositivo já cadastrado")
    
    # Inserir
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO devices (device_id, nome, placa, transporte, criado_em)
        VALUES (?, ?, ?, ?, ?)
    """, (device.device_id, device.nome, device.placa, device.transporte, now))
    
    conn.commit()
    conn.close()
    
    return {
        "device_id": device.device_id,
        "nome": device.nome,
        "placa": device.placa,
        "transporte": device.transporte,
        "criado_em": now
    }


@app.patch("/api/devices/{device_id}", response_model=Device)
async def update_device(device_id: str, update: DeviceUpdate, auth: dict = Depends(verify_token)):
    """Atualiza informações básicas de um dispositivo"""
    conn = get_db()
    cursor = conn.cursor()
    
    row = cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    
    # Atualizar apenas campos fornecidos
    if update.nome is not None:
        cursor.execute("UPDATE devices SET nome = ? WHERE device_id = ?", (update.nome, device_id))
    
    conn.commit()
    
    # Buscar atualizado
    row = cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    conn.close()
    
    device = dict(row)
    if device.get("sensores"):
        device["sensores"] = json.loads(device["sensores"])
    if device.get("calibracao"):
        device["calibracao"] = json.loads(device["calibracao"])
    
    return device


@app.post("/api/devices/{device_id}/calibration")
async def update_calibration(device_id: str, calib: CalibrationUpdate, auth: dict = Depends(verify_token)):
    """
    Atualiza calibração de um dispositivo.
    Salva no SQLite E publica via MQTT retained para aplicação em tempo real.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    row = cursor.execute("SELECT calibracao FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    
    # Carregar calibração existente ou inicializar
    current_calib = json.loads(row["calibracao"]) if row["calibracao"] else {}
    
    # Atualizar campos fornecidos
    config_mqtt = {}
    if calib.soil_dry is not None:
        current_calib["soil_dry"] = calib.soil_dry
        config_mqtt["soil_dry"] = calib.soil_dry
    if calib.soil_wet is not None:
        current_calib["soil_wet"] = calib.soil_wet
        config_mqtt["soil_wet"] = calib.soil_wet
    if calib.publish_interval is not None:
        current_calib["publish_interval"] = calib.publish_interval
        config_mqtt["publish_interval"] = calib.publish_interval
    
    # Salvar no SQLite
    cursor.execute(
        "UPDATE devices SET calibracao = ? WHERE device_id = ?",
        (json.dumps(current_calib), device_id)
    )
    conn.commit()
    conn.close()
    
    # Publicar no MQTT (retained)
    if config_mqtt:
        publish_device_config(device_id, config_mqtt)
    
    return {
        "device_id": device_id,
        "calibracao": current_calib,
        "mqtt_published": bool(config_mqtt)
    }


@app.delete("/api/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str, auth: dict = Depends(verify_token)):
    """Remove um dispositivo do registro"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    conn.commit()
    conn.close()
    return None


@app.get("/api/devices/{device_id}/data/latest")
async def get_latest_data(device_id: str, auth: dict = Depends(verify_token)):
    """Obtém as últimas leituras de um dispositivo (últimos 5 minutos)"""
    if not influx_query_api:
        raise HTTPException(status_code=503, detail="InfluxDB não disponível")
    
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -5m)
        |> filter(fn: (r) => r["_measurement"] == "sensor_data")
        |> filter(fn: (r) => r["device_id"] == "{device_id}")
        |> pivot(rowKey:["_time"], columnKey: ["sensor"], valueColumn: "_value")
        |> limit(n: 10)
    '''
    
    try:
        tables = influx_query_api.query(query, org=INFLUX_ORG)
        
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time": record.get_time().isoformat(),
                    "values": {k: v for k, v in record.values.items() if not k.startswith("_") and k not in ["device_id", "result", "table"]}
                })
        
        return {"device_id": device_id, "readings": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar InfluxDB: {str(e)}")


@app.get("/api/devices/{device_id}/data/history")
async def get_history_data(
    device_id: str,
    start: str = "-24h",
    auth: dict = Depends(verify_token)
):
    """Obtém histórico de leituras de um dispositivo"""
    if not influx_query_api:
        raise HTTPException(status_code=503, detail="InfluxDB não disponível")
    
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
        |> range(start: {start})
        |> filter(fn: (r) => r["_measurement"] == "sensor_data")
        |> filter(fn: (r) => r["device_id"] == "{device_id}")
        |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
        |> pivot(rowKey:["_time"], columnKey: ["sensor"], valueColumn: "_value")
    '''
    
    try:
        tables = influx_query_api.query(query, org=INFLUX_ORG)
        
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time": record.get_time().isoformat(),
                    "values": {k: v for k, v in record.values.items() if not k.startswith("_") and k not in ["device_id", "result", "table"]}
                })
        
        return {"device_id": device_id, "start": start, "readings": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar InfluxDB: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "mqtt_connected": mqtt_client.is_connected() if mqtt_client else False,
        "influx_connected": influx_client is not None
    }


# Servir arquivos estáticos (frontend) na raiz
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_frontend():
    """Serve o frontend HTML"""
    return FileResponse("static/index.html")


# ===== Inicialização =====
if __name__ == "__main__":
    import uvicorn
    
    # Inicializar banco de dados
    init_db()
    
    # Rodar servidor
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
