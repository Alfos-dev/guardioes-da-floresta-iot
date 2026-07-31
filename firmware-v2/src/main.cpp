// Guardioes da Floresta - Firmware v2.0 (ESP32-S3)
//
// Modular, MQTT-first firmware built in three layers:
//   config    -> NvsConfig      (runtime config in NVS, no hardcoded values)
//   sensors   -> SensorBase     (SoilMoisture, AHT10Sensor)
//   transport -> MqttTransport  (WiFi + MQTT, generic telemetry schema)
//
// Boot flow:
//   1. Load config from NVS.
//   2. If not provisioned -> start a captive AP so the user can enter WiFi/MQTT.
//   3. Otherwise connect WiFi + MQTT, subscribe to guardioes/{id}/config.
//   4. Loop: publish telemetry every publish_interval seconds; heartbeat 30s.
//   5. On config message: update NVS and apply immediately (no reflash).

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

#include "NvsConfig.h"
#include "SoilMoisture.h"
#include "AHT10Sensor.h"
#include "MqttTransport.h"

#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "2.0.0"
#endif

// ---- Fixed pinout for this ESP32-S3 board (matches the v1 wiring) ----
static const int SDA_PIN      = 17;  // AHT10 SDA
static const int SCL_PIN      = 18;  // AHT10 SCL
static const int SOIL_ADC_PIN = 4;   // Soil moisture ADC

// ---- Global objects ----
NvsConfig      gNvs;
DeviceConfig   gCfg;
MqttTransport  gTransport;
SoilMoisture*  gSoil = nullptr;
AHT10Sensor*   gAht  = nullptr;

bool           gProvisioningMode = false;
WebServer      gWebServer(80);

unsigned long  gLastPublishMs   = 0;
unsigned long  gLastHeartbeatMs = 0;
static const unsigned long HEARTBEAT_MS = 30000UL;

// ---------------------------------------------------------------------------
// Config message handler: applies a (possibly partial) config JSON to NVS and
// to the live sensor objects so the change takes effect without a reflash.
// ---------------------------------------------------------------------------
void applyConfigJson(const String& jsonPayload) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, jsonPayload);
  if (err) {
    Serial.printf("[config] JSON invalido: %s\n", err.c_str());
    return;
  }

  if (doc["publish_interval"].is<int>()) {
    int iv = doc["publish_interval"].as<int>();
    gCfg.publish_interval = iv;
    gNvs.setPublishInterval(iv);
    Serial.printf("[config] publish_interval = %d s\n", iv);
  }

  bool soilChanged = false;
  if (doc["soil_dry"].is<float>()) { gCfg.soil_dry = doc["soil_dry"].as<float>(); soilChanged = true; }
  if (doc["soil_wet"].is<float>()) { gCfg.soil_wet = doc["soil_wet"].as<float>(); soilChanged = true; }
  if (soilChanged) {
    gNvs.setSoilCalibration(gCfg.soil_dry, gCfg.soil_wet);
    if (gSoil) gSoil->setCalibration(gCfg.soil_dry, gCfg.soil_wet);
    Serial.printf("[config] soil calibracao dry=%.0f wet=%.0f\n", gCfg.soil_dry, gCfg.soil_wet);
  }

  Serial.println("[config] aplicado");
}

// ---------------------------------------------------------------------------
// Captive AP provisioning: minimal web form to capture WiFi + MQTT + device_id.
// ---------------------------------------------------------------------------
void handleRoot() {
  String html =
    "<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>Guardioes v2 - Configuracao</title></head><body style='font-family:sans-serif;max-width:420px;margin:20px auto'>"
    "<h2>Guardioes da Floresta v2</h2><p>Configuracao inicial do dispositivo</p>"
    "<form method='POST' action='/save'>"
    "Device ID:<br><input name='device_id' value='esp32s3_01' style='width:100%'><br><br>"
    "WiFi SSID:<br><input name='wifi_ssid' style='width:100%'><br><br>"
    "WiFi Senha:<br><input name='wifi_pass' type='password' style='width:100%'><br><br>"
    "MQTT Host:<br><input name='mqtt_host' style='width:100%'><br><br>"
    "MQTT Porta:<br><input name='mqtt_port' value='1883' style='width:100%'><br><br>"
    "MQTT Usuario:<br><input name='mqtt_user' style='width:100%'><br><br>"
    "MQTT Senha:<br><input name='mqtt_pass' type='password' style='width:100%'><br><br>"
    "Intervalo (s):<br><input name='publish_interval' value='60' style='width:100%'><br><br>"
    "<button type='submit' style='padding:10px 20px'>Salvar e reiniciar</button>"
    "</form></body></html>";
  gWebServer.send(200, "text/html", html);
}

void handleSave() {
  DeviceConfig cfg;
  memset(&cfg, 0, sizeof(cfg));
  strncpy(cfg.device_id, gWebServer.arg("device_id").c_str(), sizeof(cfg.device_id) - 1);
  strncpy(cfg.wifi_ssid, gWebServer.arg("wifi_ssid").c_str(), sizeof(cfg.wifi_ssid) - 1);
  strncpy(cfg.wifi_pass, gWebServer.arg("wifi_pass").c_str(), sizeof(cfg.wifi_pass) - 1);
  strncpy(cfg.mqtt_host, gWebServer.arg("mqtt_host").c_str(), sizeof(cfg.mqtt_host) - 1);
  strncpy(cfg.mqtt_user, gWebServer.arg("mqtt_user").c_str(), sizeof(cfg.mqtt_user) - 1);
  strncpy(cfg.mqtt_pass, gWebServer.arg("mqtt_pass").c_str(), sizeof(cfg.mqtt_pass) - 1);
  cfg.mqtt_port        = gWebServer.arg("mqtt_port").toInt();
  cfg.publish_interval = gWebServer.arg("publish_interval").toInt();
  if (cfg.mqtt_port <= 0)        cfg.mqtt_port = 1883;
  if (cfg.publish_interval <= 0) cfg.publish_interval = 60;
  // Keep default calibration; it can be tuned later over MQTT.
  cfg.soil_dry = 4065.0f;
  cfg.soil_wet = 1150.0f;

  gNvs.save(cfg);
  gWebServer.send(200, "text/html",
                  "<html><body><h3>Configuracao salva. Reiniciando...</h3></body></html>");
  delay(1500);
  ESP.restart();
}

void startProvisioningAP() {
  gProvisioningMode = true;
  String apName = "Guardioes-Setup";
  Serial.printf("[provisioning] NVS vazia. Iniciando AP '%s' (192.168.4.1)\n", apName.c_str());
  WiFi.mode(WIFI_AP);
  WiFi.softAP(apName.c_str());
  gWebServer.on("/", handleRoot);
  gWebServer.on("/save", HTTP_POST, handleSave);
  gWebServer.begin();
}

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.printf("\n[boot] Guardioes da Floresta v%s\n", FIRMWARE_VERSION);

  gNvs.begin();
  bool provisioned = gNvs.load(gCfg);

  if (!provisioned) {
    startProvisioningAP();
    return;  // stay in AP mode until configured + rebooted
  }

  Serial.printf("[boot] device_id=%s, intervalo=%ds\n", gCfg.device_id, gCfg.publish_interval);

  // Instantiate sensors with calibration from NVS.
  gSoil = new SoilMoisture(SOIL_ADC_PIN, gCfg.soil_dry, gCfg.soil_wet);
  gAht  = new AHT10Sensor(SDA_PIN, SCL_PIN);
  gSoil->begin();
  if (!gAht->begin()) {
    Serial.println("[boot] AVISO: AHT10 nao encontrado em 17/18");
  }

  // Configure and connect transport.
  gTransport.configure(gCfg.device_id,
                       gCfg.wifi_ssid, gCfg.wifi_pass,
                       gCfg.mqtt_host, gCfg.mqtt_port,
                       gCfg.mqtt_user, gCfg.mqtt_pass);
  gTransport.onConfig(applyConfigJson);
  gTransport.begin();
}

void loop() {
  if (gProvisioningMode) {
    gWebServer.handleClient();
    return;
  }

  gTransport.loop();

  unsigned long now = millis();

  // Telemetry at publish_interval.
  if (now - gLastPublishMs >= (unsigned long)gCfg.publish_interval * 1000UL) {
    gLastPublishMs = now;

    Reading readings[4];
    int n = 0;
    if (gSoil) {
      readings[n] = gSoil->read();
      if (readings[n].valid) n++;
    }
    if (gAht && gAht->available()) {
      n += gAht->readAll(&readings[n], 4 - n);
    }
    gTransport.publishTelemetry(readings, n);
  }

  // Heartbeat every 30s.
  if (now - gLastHeartbeatMs >= HEARTBEAT_MS) {
    gLastHeartbeatMs = now;
    gTransport.publishStatus(true);
  }
}
