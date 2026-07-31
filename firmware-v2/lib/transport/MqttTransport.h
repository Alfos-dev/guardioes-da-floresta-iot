#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "SensorBase.h"

// Layer 3 of the firmware architecture: transport driver.
//
// Handles the WiFi connection and the MQTT broker session, and knows how to
// serialize readings into the generic telemetry schema. It is deliberately
// decoupled from the sensor drivers - it only receives Reading structs.
//
// Topics:
//   publish   guardioes/{device_id}/telemetry   (QoS 1)
//   subscribe guardioes/{device_id}/config      (retained, QoS 1)
//   publish   guardioes/{device_id}/status      (heartbeat)

// Callback invoked when a retained config message is received. The raw JSON
// payload is passed through so the sketch can apply it to NVS + sensors.
typedef std::function<void(const String& jsonPayload)> ConfigCallback;

class MqttTransport {
public:
  MqttTransport();

  // Stores connection parameters (does not connect yet).
  void configure(const char* deviceId,
                 const char* wifiSsid, const char* wifiPass,
                 const char* mqttHost, int mqttPort,
                 const char* mqttUser, const char* mqttPass);

  // Registers the callback for incoming config messages.
  void onConfig(ConfigCallback cb) { _configCb = cb; }

  // Connects WiFi then the MQTT broker. Returns true on success.
  bool begin();

  // Keeps WiFi + MQTT alive and processes incoming messages. Call frequently.
  void loop();

  bool connected();

  // Publishes the generic telemetry payload built from the readings array.
  bool publishTelemetry(const Reading* readings, int count);

  // Publishes the heartbeat status payload: {"online":true,"fw":"..."}.
  bool publishStatus(bool online);

private:
  WiFiClient    _wifiClient;
  PubSubClient  _mqtt;

  String _deviceId;
  String _wifiSsid, _wifiPass;
  String _mqttHost, _mqttUser, _mqttPass;
  int    _mqttPort;

  String _topicTelemetry;
  String _topicConfig;
  String _topicStatus;

  ConfigCallback _configCb;

  bool ensureWifi();
  bool ensureMqtt();
  void handleMessage(char* topic, byte* payload, unsigned int length);
};
