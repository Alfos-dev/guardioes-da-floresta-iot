# Firmware v2.0 — Guardiões da Floresta

Firmware modular, MQTT-first, para o nó sensor da v2.0. O firmware v1.0
(estável) é publicado de forma independente na release `v1.0.0` (branch
`release/v1`); no `main` seu código fica em `legacy/` apenas como referência.

## Placas Suportadas

| Placa | Chip | WiFi | Bluetooth | Flash | RAM | Status |
|-------|------|------|-----------|-------|-----|--------|
| **ESP32-S3 DevKit C-1** | Xtensa LX7 dual-core | 802.11 b/g/n | BLE 5.0 | 8MB | 512KB | ✅ Recomendado |
| **ESP32 DOIT DevKit V1** | Xtensa LX6 dual-core | 802.11 b/g/n | BLE 4.2 | 4MB | 520KB | ✅ Custo-benefício |

**Ambas as placas** atendem todos os requisitos do projeto e usam o **mesmo código-fonte**.

## Arquitetura em camadas

```
lib/config/     NvsConfig      -> configuração persistente na NVS (sem hardcode)
lib/sensors/    SensorBase     -> interface comum Reading{sensor,value,unit}
                SoilMoisture   -> ADC + calibração dry/wet (da NVS)
                AHT10Sensor    -> temperatura + umidade do ar (I2C)
lib/transport/  MqttTransport  -> WiFi + MQTT (publica telemetria, assina config)
src/main.cpp    boot + provisioning (AP) + loop de publicação + callback de config
```

## Build / Upload (local e offline)

### Para ESP32-S3 DevKit C-1:
```bash
pio run -e esp32s3_v2            # compila
pio run -e esp32s3_v2 -t upload  # grava no dispositivo
pio device monitor -b 115200     # monitor serial
```

### Para ESP32 DOIT DevKit V1:
```bash
pio run -e esp32_doit_v2         # compila
pio run -e esp32_doit_v2 -t upload  # grava no dispositivo
pio device monitor -b 115200     # monitor serial
```

Após o primeiro `pio run`, as bibliotecas e o toolchain ficam em cache
(`~/.platformio`), permitindo builds totalmente offline.

## Pinagem Recomendada

### ESP32-S3 DevKit C-1

| Sensor/Componente | Pino | Tipo | Observação |
|-------------------|------|------|------------|
| AHT10 SDA | GPIO8 | I2C | Sensor temp/umidade |
| AHT10 SCL | GPIO9 | I2C | Sensor temp/umidade |
| Solo (analógico) | GPIO1 | ADC | Sensor capacitivo/resistivo |

### ESP32 DOIT DevKit V1

| Sensor/Componente | Pino | Tipo | Observação |
|-------------------|------|------|------------|
| AHT10 SDA | GPIO21 | I2C | Padrão I2C |
| AHT10 SCL | GPIO22 | I2C | Padrão I2C |
| Solo (analógico) | GPIO34 | ADC1 | Input-only, sem conflito WiFi |

**⚠️ Pinos a evitar no ESP32 DOIT DevKit:**
- GPIO 6-11: Conectados à flash interna
- GPIO 0, 2, 5, 12, 15: Boot strapping pins (podem impedir boot)
- ADC2 (GPIO 0, 2, 4, 12-15, 25-27): Não funcionam com WiFi ativo

**💡 Ajuste no código (se necessário):**

Se você usar pinos diferentes, atualize em `src/main.cpp`:

```cpp
// Para ESP32-S3 (padrão):
SoilMoisture gSoil(1);      // GPIO1
AHT10Sensor gAht(8, 9);     // SDA=GPIO8, SCL=GPIO9

// Para ESP32 DOIT DevKit V1:
SoilMoisture gSoil(34);     // GPIO34 (ADC1_6)
AHT10Sensor gAht(21, 22);   // SDA=GPIO21, SCL=GPIO22
```

## Provisionamento inicial

Com a NVS vazia, o dispositivo cria o Wi-Fi `Guardioes-Setup`
(IP `192.168.4.1`). Conecte-se e preencha o formulário com Wi-Fi, broker MQTT e
`device_id`. Após salvar, o dispositivo reinicia e passa a publicar telemetria.

## Tópicos MQTT

| Tópico | Direção | QoS | Retained |
| :--- | :--- | :--- | :--- |
| `guardioes/{device_id}/telemetry` | publica | 1 | não |
| `guardioes/{device_id}/config`    | assina  | 1 | sim |
| `guardioes/{device_id}/status`    | publica | — | sim (heartbeat 30s + last will) |

## Reconfiguração remota (sem reflash)

Publicar um JSON retido em `guardioes/{device_id}/config` aplica a mudança na
hora e persiste na NVS. Campos suportados:

```json
{ "publish_interval": 30, "soil_dry": 4065, "soil_wet": 1150 }
```
