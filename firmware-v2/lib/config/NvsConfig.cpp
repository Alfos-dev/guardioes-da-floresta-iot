#include "NvsConfig.h"
#include <Preferences.h>

// Default values applied whenever a key is missing from NVS.
static const int   DEFAULT_MQTT_PORT        = 1883;
static const int   DEFAULT_PUBLISH_INTERVAL = 60;
static const float DEFAULT_SOIL_DRY         = 4065.0f;
static const float DEFAULT_SOIL_WET         = 1150.0f;

bool NvsConfig::begin() {
  // Nothing to keep open globally; each operation opens its own handle so we
  // never hold NVS locked longer than necessary.
  return true;
}

bool NvsConfig::load(DeviceConfig& cfg) {
  Preferences p;
  if (!p.begin(NAMESPACE, /*readOnly=*/true)) {
    // Namespace does not exist yet -> not provisioned. Fill defaults.
    memset(&cfg, 0, sizeof(cfg));
    cfg.mqtt_port        = DEFAULT_MQTT_PORT;
    cfg.publish_interval = DEFAULT_PUBLISH_INTERVAL;
    cfg.soil_dry         = DEFAULT_SOIL_DRY;
    cfg.soil_wet         = DEFAULT_SOIL_WET;
    return false;
  }

  memset(&cfg, 0, sizeof(cfg));
  p.getString("device_id", cfg.device_id, sizeof(cfg.device_id));
  p.getString("wifi_ssid", cfg.wifi_ssid, sizeof(cfg.wifi_ssid));
  p.getString("wifi_pass", cfg.wifi_pass, sizeof(cfg.wifi_pass));
  p.getString("mqtt_host", cfg.mqtt_host, sizeof(cfg.mqtt_host));
  p.getString("mqtt_user", cfg.mqtt_user, sizeof(cfg.mqtt_user));
  p.getString("mqtt_pass", cfg.mqtt_pass, sizeof(cfg.mqtt_pass));
  cfg.mqtt_port        = p.getInt("mqtt_port", DEFAULT_MQTT_PORT);
  cfg.publish_interval = p.getInt("pub_int", DEFAULT_PUBLISH_INTERVAL);
  cfg.soil_dry         = p.getFloat("soil_dry", DEFAULT_SOIL_DRY);
  cfg.soil_wet         = p.getFloat("soil_wet", DEFAULT_SOIL_WET);
  p.end();

  return strlen(cfg.device_id) > 0 && strlen(cfg.wifi_ssid) > 0;
}

bool NvsConfig::save(const DeviceConfig& cfg) {
  Preferences p;
  if (!p.begin(NAMESPACE, /*readOnly=*/false)) return false;
  p.putString("device_id", cfg.device_id);
  p.putString("wifi_ssid", cfg.wifi_ssid);
  p.putString("wifi_pass", cfg.wifi_pass);
  p.putString("mqtt_host", cfg.mqtt_host);
  p.putString("mqtt_user", cfg.mqtt_user);
  p.putString("mqtt_pass", cfg.mqtt_pass);
  p.putInt("mqtt_port", cfg.mqtt_port);
  p.putInt("pub_int", cfg.publish_interval);
  p.putFloat("soil_dry", cfg.soil_dry);
  p.putFloat("soil_wet", cfg.soil_wet);
  p.end();
  return true;
}

bool NvsConfig::isProvisioned() {
  Preferences p;
  if (!p.begin(NAMESPACE, /*readOnly=*/true)) return false;
  String id   = p.getString("device_id", "");
  String ssid = p.getString("wifi_ssid", "");
  p.end();
  return id.length() > 0 && ssid.length() > 0;
}

void NvsConfig::setPublishInterval(int seconds) {
  if (seconds <= 0) return;
  Preferences p;
  if (!p.begin(NAMESPACE, false)) return;
  p.putInt("pub_int", seconds);
  p.end();
}

void NvsConfig::setSoilCalibration(float dry, float wet) {
  Preferences p;
  if (!p.begin(NAMESPACE, false)) return;
  p.putFloat("soil_dry", dry);
  p.putFloat("soil_wet", wet);
  p.end();
}

void NvsConfig::setWifi(const char* ssid, const char* pass) {
  Preferences p;
  if (!p.begin(NAMESPACE, false)) return;
  if (ssid) p.putString("wifi_ssid", ssid);
  if (pass) p.putString("wifi_pass", pass);
  p.end();
}

void NvsConfig::setMqtt(const char* host, int port, const char* user, const char* pass) {
  Preferences p;
  if (!p.begin(NAMESPACE, false)) return;
  if (host) p.putString("mqtt_host", host);
  if (port > 0) p.putInt("mqtt_port", port);
  if (user) p.putString("mqtt_user", user);
  if (pass) p.putString("mqtt_pass", pass);
  p.end();
}

void NvsConfig::setDeviceId(const char* id) {
  if (!id) return;
  Preferences p;
  if (!p.begin(NAMESPACE, false)) return;
  p.putString("device_id", id);
  p.end();
}

void NvsConfig::clear() {
  Preferences p;
  if (!p.begin(NAMESPACE, false)) return;
  p.clear();
  p.end();
}
