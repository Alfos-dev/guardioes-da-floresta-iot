#pragma once
#include <Arduino.h>

// Persistent device configuration stored in NVS (non-volatile storage).
//
// Layer 1 of the firmware architecture: runtime configuration.
// Nothing here is hardcoded in the .cpp files - the device reads everything
// from NVS at boot, which is what allows the admin panel to reconfigure the
// device over MQTT without a reflash.
struct DeviceConfig {
  char  device_id[32];
  char  wifi_ssid[64];
  char  wifi_pass[64];
  char  mqtt_host[64];
  int   mqtt_port;         // default 1883
  char  mqtt_user[32];
  char  mqtt_pass[32];
  int   publish_interval;  // seconds, default 60
  float soil_dry;          // calibration: raw ADC value when soil is dry
  float soil_wet;          // calibration: raw ADC value when soil is wet
};

class NvsConfig {
public:
  // Opens the NVS namespace. Call once in setup().
  bool begin();

  // Loads the full config into `cfg`. Missing keys fall back to defaults.
  // Returns false when the device has never been provisioned (no device_id).
  bool load(DeviceConfig& cfg);

  // Persists the full config to NVS.
  bool save(const DeviceConfig& cfg);

  // True when NVS holds a usable configuration (device_id + wifi_ssid set).
  bool isProvisioned();

  // Convenience helpers used by the MQTT config callback so a partial config
  // message only overwrites the fields it actually carries.
  void setPublishInterval(int seconds);
  void setSoilCalibration(float dry, float wet);
  void setWifi(const char* ssid, const char* pass);
  void setMqtt(const char* host, int port, const char* user, const char* pass);
  void setDeviceId(const char* id);

  // Wipes all stored configuration (used to force re-provisioning).
  void clear();

private:
  static constexpr const char* NAMESPACE = "gdf_cfg";
};
