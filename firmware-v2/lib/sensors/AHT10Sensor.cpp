#include "AHT10Sensor.h"
#include <Wire.h>

AHT10Sensor::AHT10Sensor(int sdaPin, int sclPin)
    : _sdaPin(sdaPin), _sclPin(sclPin), _ok(false) {}

bool AHT10Sensor::begin() {
  Wire.begin(_sdaPin, _sclPin);
  _ok = _aht.begin();
  return _ok;
}

Reading AHT10Sensor::read() {
  if (!_ok) return Reading();  // invalid
  sensors_event_t humidity, temp;
  _aht.getEvent(&humidity, &temp);
  return Reading("air_temp", temp.temperature, "C");
}

int AHT10Sensor::readAll(Reading* out, int maxCount) {
  if (!_ok || maxCount < 1) return 0;
  sensors_event_t humidity, temp;
  _aht.getEvent(&humidity, &temp);

  int n = 0;
  out[n++] = Reading("air_temp", temp.temperature, "C");
  if (n < maxCount) {
    out[n++] = Reading("air_humidity", humidity.relative_humidity, "%");
  }
  return n;
}
