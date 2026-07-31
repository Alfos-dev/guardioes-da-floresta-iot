#include "MqttTransport.h"
#include <ArduinoJson.h>

#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "2.0.0"
#endif

static const unsigned long WIFI_TIMEOUT_MS = 20000UL;

MqttTransport::MqttTransport() : _mqtt(_wifiClient), _mqttPort(1883) {}

void MqttTransport::configure(const char* deviceId,
                              const char* wifiSsid, const char* wifiPass,
                              const char* mqttHost, int mqttPort,
                              const char* mqttUser, const char* mqttPass) {
  _deviceId = deviceId;
  _wifiSsid = wifiSsid;
  _wifiPass = wifiPass;
  _mqttHost = mqttHost;
  _mqttPort = mqttPort;
  _mqttUser = mqttUser;
  _mqttPass = mqttPass;

  _topicTelemetry = "guardioes/" + _deviceId + "/telemetry";
  _topicConfig    = "guardioes/" + _deviceId + "/config";
  _topicStatus    = "guardioes/" + _deviceId + "/status";

  _mqtt.setServer(_mqttHost.c_str(), _mqttPort);
  _mqtt.setBufferSize(1024);  // telemetry payloads can exceed the 256B default
  _mqtt.setCallback([this](char* t, byte* p, unsigned int l) {
    this->handleMessage(t, p, l);
  });
}

bool MqttTransport::ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;

  Serial.printf("[wifi] conectando a %s ...\n", _wifiSsid.c_str());
  WiFi.mode(WIFI_STA);
  WiFi.begin(_wifiSsid.c_str(), _wifiPass.c_str());

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[wifi] conectado, IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }
  Serial.println("[wifi] falha na conexao");
  return false;
}

bool MqttTransport::ensureMqtt() {
  if (_mqtt.connected()) return true;
  if (!ensureWifi()) return false;

  Serial.printf("[mqtt] conectando ao broker %s:%d ...\n", _mqttHost.c_str(), _mqttPort);

  // Last will: broker publishes offline status if the device drops.
  String willPayload = "{\"online\":false}";
  bool ok = _mqtt.connect(_deviceId.c_str(),
                          _mqttUser.c_str(), _mqttPass.c_str(),
                          _topicStatus.c_str(), 1, true, willPayload.c_str());
  if (ok) {
    Serial.println("[mqtt] conectado");
    // Subscribe to the retained config topic (QoS 1) to receive remote config.
    _mqtt.subscribe(_topicConfig.c_str(), 1);
    publishStatus(true);
  } else {
    Serial.printf("[mqtt] falha, rc=%d\n", _mqtt.state());
  }
  return ok;
}

bool MqttTransport::begin() {
  if (!ensureWifi()) return false;
  return ensureMqtt();
}

void MqttTransport::loop() {
  if (!_mqtt.connected()) {
    ensureMqtt();
  }
  _mqtt.loop();
}

bool MqttTransport::connected() {
  return _mqtt.connected();
}

bool MqttTransport::publishTelemetry(const Reading* readings, int count) {
  if (!ensureMqtt()) return false;

  JsonDocument doc;
  doc["device_id"] = _deviceId;
  doc["timestamp"] = "";  // server timestamps on ingest; kept for schema shape
  JsonArray arr = doc["readings"].to<JsonArray>();
  for (int i = 0; i < count; ++i) {
    if (!readings[i].valid) continue;
    JsonObject r = arr.add<JsonObject>();
    r["sensor"] = readings[i].sensor;
    r["value"]  = readings[i].value;
    r["unit"]   = readings[i].unit;
  }

  String out;
  serializeJson(doc, out);
  bool ok = _mqtt.publish(_topicTelemetry.c_str(), out.c_str(), false);
  Serial.printf("[mqtt] telemetry -> %s (%s)\n", _topicTelemetry.c_str(), ok ? "ok" : "erro");
  return ok;
}

bool MqttTransport::publishStatus(bool online) {
  if (!_mqtt.connected()) return false;
  JsonDocument doc;
  doc["online"] = online;
  doc["fw"]     = FIRMWARE_VERSION;
  String out;
  serializeJson(doc, out);
  return _mqtt.publish(_topicStatus.c_str(), out.c_str(), true);
}

void MqttTransport::handleMessage(char* topic, byte* payload, unsigned int length) {
  String t(topic);
  String msg;
  msg.reserve(length);
  for (unsigned int i = 0; i < length; ++i) msg += (char)payload[i];

  Serial.printf("[mqtt] msg em %s: %s\n", topic, msg.c_str());

  if (t == _topicConfig && _configCb) {
    _configCb(msg);
  }
}
