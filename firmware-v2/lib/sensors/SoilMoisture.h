#pragma once
#include "SensorBase.h"

// Capacitive/resistive soil moisture sensor read through an ADC pin.
//
// The raw ADC value is converted to a percentage using the dry/wet
// calibration points, which come from NVS config so they can be adjusted
// remotely by the admin panel without a reflash.
class SoilMoisture : public SensorBase {
public:
  SoilMoisture(int adcPin, float rawDry, float rawWet);

  bool    begin() override;
  Reading read() override;

  // Updates the calibration at runtime (called when a config message arrives).
  void setCalibration(float rawDry, float rawWet);

  // Exposes the last raw ADC reading for diagnostics.
  int lastRaw() const { return _lastRaw; }

private:
  int   _adcPin;
  float _rawDry;
  float _rawWet;
  int   _lastRaw;

  int readRawAveraged(int samples = 10);
};
