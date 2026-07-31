#pragma once
#include "SensorBase.h"
#include <Adafruit_AHTX0.h>

// AHT10 temperature + humidity sensor over I2C.
//
// This driver exposes two readings ("air_temp" and "air_humidity"), so it
// overrides readAll(). read() returns the temperature as the primary value.
class AHT10Sensor : public SensorBase {
public:
  AHT10Sensor(int sdaPin, int sclPin);

  bool    begin() override;
  Reading read() override;                              // primary: air_temp
  int     readAll(Reading* out, int maxCount) override; // air_temp + air_humidity

  bool available() const { return _ok; }

private:
  int              _sdaPin;
  int              _sclPin;
  Adafruit_AHTX0   _aht;
  bool             _ok;
};
