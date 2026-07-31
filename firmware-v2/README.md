# Firmware v2.0 — Guardiões da Floresta (ESP32-S3)

Firmware modular, MQTT-first, para o nó sensor da v2.0. Convive com o firmware
v1.0 que permanece na raiz do repositório (`src/`, `platformio.ini`).

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

```bash
pio run -e esp32s3_v2            # compila
pio run -e esp32s3_v2 -t upload  # grava no dispositivo
pio device monitor -b 115200     # monitor serial
```

Após o primeiro `pio run`, as bibliotecas e o toolchain ficam em cache
(`~/.platformio`), permitindo builds totalmente offline.

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
