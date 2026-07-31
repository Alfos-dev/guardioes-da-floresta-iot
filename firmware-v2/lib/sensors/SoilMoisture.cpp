#include "SoilMoisture.h"

SoilMoisture::SoilMoisture(int adcPin, float rawDry, float rawWet)
    : _adcPin(adcPin), _rawDry(rawDry), _rawWet(rawWet), _lastRaw(0) {}

bool SoilMoisture::begin() {
  analogReadResolution(12);
#ifdef analogSetPinAttenuation
  analogSetPinAttenuation(_adcPin, ADC_11db);
#endif
  return true;  // ADC pin is always available on ESP32-S3
}

int SoilMoisture::readRawAveraged(int samples) {
  long sum = 0;
  for (int i = 0; i < samples; ++i) {
    sum += analogRead(_adcPin);
    delay(10);
  }
  return (int)(sum / samples);
}

Reading SoilMoisture::read() {
  _lastRaw = readRawAveraged();

  // Map raw -> percentage using the dry/wet calibration points.
  // dry corresponds to 0%, wet corresponds to 100%.
  float span = _rawDry - _rawWet;
  float pct  = 0.0f;
  if (span != 0.0f) {
    pct = (float)(_rawDry - _lastRaw) * 100.0f / span;
  }
  if (pct < 0.0f)   pct = 0.0f;
  if (pct > 100.0f) pct = 100.0f;

  return Reading("soil_moisture", pct, "%");
}

void SoilMoisture::setCalibration(float rawDry, float rawWet) {
  _rawDry = rawDry;
  _rawWet = rawWet;
}
