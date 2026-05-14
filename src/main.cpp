#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_AHTX0.h>

// ----- CONFIG PINOUT -----
const char* DEVICE_ID = "esp32_1";

const int SDA_PIN = 17;      // AHT10 SDA no 17
const int SCL_PIN = 18;      // AHT10 SCL no 18
const int SOIL_ADC_PIN = 4;  // Solo no 4

int SOIL_RAW_DRY  = 4065;   
int SOIL_RAW_WET  = 1150;   

const unsigned long MEASURE_INTERVAL_MS = 5000UL; 
// ------------------------------

Adafruit_AHTX0 aht;
bool aht_ok = false;
unsigned long seq = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n{\"info\":\"boot_test_17_18\",\"device\":\"" + String(DEVICE_ID) + "\"}");

  // I2C nos pinos 17 e 18
  Wire.begin(SDA_PIN, SCL_PIN);

  analogReadResolution(12);
  #ifdef analogSetPinAttenuation
    analogSetPinAttenuation(SOIL_ADC_PIN, ADC_11db);
  #endif

  // Inicializa AHT10
  if (aht.begin()) {
    aht_ok = true;
    Serial.println("{\"info\":\"AHT10 found on 17/18\"}");
  } else {
    aht_ok = false;
    Serial.println("{\"warning\":\"AHT10 not found no 17/18!\"}");
  }
}

int readSoilRaw() {
  const int N = 10;
  long sum = 0;
  for (int i = 0; i < N; ++i) { sum += analogRead(SOIL_ADC_PIN); delay(10); }
  return (int)(sum / N);
}

void loop() {
  seq++;
  sensors_event_t humidity, temp;
  
  if (aht_ok) aht.getEvent(&humidity, &temp);

  int raw = readSoilRaw();
  int soil_pct = map(raw, SOIL_RAW_DRY, SOIL_RAW_WET, 0, 100);
  if (soil_pct < 0) soil_pct = 0; if (soil_pct > 100) soil_pct = 100;

  // JSON para o Monitor
  Serial.print("{\"device_id\":\"" + String(DEVICE_ID) + "\",\"seq\":" + String(seq) + ",");
  if (aht_ok) {
    Serial.print("\"t\":" + String(temp.temperature) + ",\"ha\":" + String(humidity.relative_humidity) + ",");
  } else {
    Serial.print("\"t\":null,\"ha\":null,");
  }
  Serial.println("\"s\":" + String(soil_pct) + ",\"soil_raw\":" + String(raw) + "}");

  delay(MEASURE_INTERVAL_MS);
}