#pragma once
#include <Arduino.h>

// Layer 2 of the firmware architecture: sensor drivers.
//
// Every sensor driver implements this common interface, so the main loop can
// iterate over a list of sensors without knowing their concrete type. Adding a
// new sensor to the catalog only means adding a new class here - no change to
// the transport or config layers (see RNF07).

// A single normalized measurement matching the generic ingestion schema:
//   { "sensor": "soil_moisture", "value": 42, "unit": "%" }
struct Reading {
  String sensor;  // logical sensor name, e.g. "soil_moisture", "air_temp"
  float  value;   // measured value
  String unit;    // unit string, e.g. "%", "C"
  bool   valid;   // false when the read failed (sensor absent / error)

  Reading() : sensor(""), value(0.0f), unit(""), valid(false) {}
  Reading(const String& s, float v, const String& u)
      : sensor(s), value(v), unit(u), valid(true) {}
};

class SensorBase {
public:
  virtual ~SensorBase() {}

  // Initializes the sensor hardware. Returns false when the sensor is absent.
  virtual bool begin() = 0;

  // Performs a measurement. Some drivers (e.g. AHT10) expose multiple values;
  // read() returns the primary one and readAll() returns the full set.
  virtual Reading read() = 0;

  // Fills `out` with up to `maxCount` readings, returning how many were
  // written. Single-value sensors return 1. Default implementation delegates
  // to read().
  virtual int readAll(Reading* out, int maxCount) {
    if (maxCount < 1) return 0;
    out[0] = read();
    return out[0].valid ? 1 : 0;
  }
};
