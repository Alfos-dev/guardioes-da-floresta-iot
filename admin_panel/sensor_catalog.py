"""
Catálogo de sensores suportados pelo firmware v2.0
Define sensores disponíveis, suas interfaces e configurações
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class SensorPin(BaseModel):
    """Definição de um pino do sensor"""
    name: str  # Nome lógico (ex: "SDA", "SCL", "SIGNAL")
    type: str  # Tipo: "I2C_SDA", "I2C_SCL", "ADC", "DIGITAL"
    gpio_esp32s3: Optional[int] = None  # GPIO padrão para ESP32-S3
    gpio_esp32: Optional[int] = None    # GPIO padrão para ESP32 DOIT DevKit
    required: bool = True  # Se o pino é obrigatório


class SensorDefinition(BaseModel):
    """Definição de um sensor no catálogo"""
    id: str  # Identificador único (ex: "aht10")
    name: str  # Nome completo (ex: "AHT10 Temp/Humidity")
    category: str  # Categoria: "temperature", "humidity", "soil", "light", etc
    interface: str  # Interface: "I2C", "ADC", "DIGITAL", "SPI"
    description: str  # Descrição do sensor
    library: str  # Biblioteca PlatformIO necessária
    header_file: str  # Header file a incluir
    class_name: str  # Nome da classe C++
    readings: List[str]  # Leituras que o sensor fornece (ex: ["air_temperature", "air_humidity"])
    pins: List[SensorPin]  # Pinos necessários
    calibration: bool = False  # Se requer calibração
    init_code: str = ""  # Código de inicialização (opcional)
    read_code: str = ""  # Código de leitura (opcional)


# ===== CATÁLOGO DE SENSORES =====

SENSOR_CATALOG: List[SensorDefinition] = [
    # Sensor de temperatura e umidade do ar AHT10
    SensorDefinition(
        id="aht10",
        name="AHT10 Temp/Humidity Sensor",
        category="environmental",
        interface="I2C",
        description="Sensor de temperatura e umidade do ar de alta precisão (I2C)",
        library="adafruit/Adafruit AHTX0 @ ^2.0.5",
        header_file="lib/sensors/AHT10Sensor.h",
        class_name="AHT10Sensor",
        readings=["air_temperature", "air_humidity"],
        pins=[
            SensorPin(
                name="SDA",
                type="I2C_SDA",
                gpio_esp32s3=8,
                gpio_esp32=21,
                required=True
            ),
            SensorPin(
                name="SCL",
                type="I2C_SCL",
                gpio_esp32s3=9,
                gpio_esp32=22,
                required=True
            )
        ],
        calibration=False,
        init_code="AHT10Sensor gAht({sda_pin}, {scl_pin});",
        read_code="gAht.readAll()"
    ),
    
    # Sensor de umidade do solo (capacitivo/resistivo)
    SensorDefinition(
        id="soil_moisture",
        name="Soil Moisture Sensor (Capacitive/Resistive)",
        category="soil",
        interface="ADC",
        description="Sensor de umidade do solo analógico, requer calibração (seco/molhado)",
        library="",  # Sem biblioteca externa
        header_file="lib/sensors/SoilMoisture.h",
        class_name="SoilMoisture",
        readings=["soil_moisture"],
        pins=[
            SensorPin(
                name="SIGNAL",
                type="ADC",
                gpio_esp32s3=1,
                gpio_esp32=34,  # ADC1_6, input-only, sem conflito WiFi
                required=True
            )
        ],
        calibration=True,
        init_code="SoilMoisture gSoil({signal_pin});",
        read_code="gSoil.read()"
    ),
    
    # Sensor DHT22 (alternativa ao AHT10)
    SensorDefinition(
        id="dht22",
        name="DHT22 Temp/Humidity Sensor",
        category="environmental",
        interface="DIGITAL",
        description="Sensor de temperatura e umidade do ar DHT22 (digital 1-wire)",
        library="adafruit/DHT sensor library @ ^1.4.4",
        header_file="DHT.h",
        class_name="DHT",
        readings=["air_temperature", "air_humidity"],
        pins=[
            SensorPin(
                name="DATA",
                type="DIGITAL",
                gpio_esp32s3=10,
                gpio_esp32=4,
                required=True
            )
        ],
        calibration=False,
        init_code="DHT gDht({data_pin}, DHT22);",
        read_code="// Custom DHT22 read code"
    ),
    
    # Sensor de luminosidade LDR
    SensorDefinition(
        id="ldr",
        name="LDR Light Sensor",
        category="light",
        interface="ADC",
        description="Sensor de luminosidade (fotoresistor)",
        library="",  # Sem biblioteca externa
        header_file="",  # Código inline
        class_name="",
        readings=["light_intensity"],
        pins=[
            SensorPin(
                name="SIGNAL",
                type="ADC",
                gpio_esp32s3=2,
                gpio_esp32=35,  # ADC1_7, input-only
                required=True
            )
        ],
        calibration=False,
        init_code="// LDR inline code",
        read_code="analogRead({signal_pin})"
    ),
]


def get_sensor_by_id(sensor_id: str) -> Optional[SensorDefinition]:
    """Retorna definição de um sensor por ID"""
    for sensor in SENSOR_CATALOG:
        if sensor.id == sensor_id:
            return sensor
    return None


def get_sensors_by_category(category: str) -> List[SensorDefinition]:
    """Retorna sensores de uma categoria específica"""
    return [s for s in SENSOR_CATALOG if s.category == category]


def validate_sensor_ids(sensor_ids: List[str]) -> bool:
    """Valida se todos os IDs de sensores existem no catálogo"""
    catalog_ids = {s.id for s in SENSOR_CATALOG}
    return all(sid in catalog_ids for sid in sensor_ids)
