/**
 * ESP32 Water Quality Sensor Node
 * Sends data to the Python Backend via Serial
 * Data Format: sensor_id,ph,temperature,turbidity,tds
 */

#include <Arduino.h>

// Configuration
const char* SENSOR_ID = "ESP32_NODE_01";
const int BAUD_RATE = 115200;

// Sensor Pins (Adjust based on your wiring)
const int PH_PIN = 34;
const int TEMP_PIN = 35;
const int TURB_PIN = 32;
const int TDS_PIN = 33;

void setup() {
  Serial.begin(BAUD_RATE);
  delay(1000);
  // Serial.println("ESP32 Sensor Node Started");
}

float readPH() {
  int raw = analogRead(PH_PIN);
  // Example calibration: 0-4095 -> 0-14 pH
  return (raw / 4095.0) * 14.0; 
}

float readTemp() {
  int raw = analogRead(TEMP_PIN);
  // Example: simple linear mapping
  return 20.0 + (raw / 4095.0) * 15.0; 
}

float readTurbidity() {
  int raw = analogRead(TURB_PIN);
  return (raw / 4095.0) * 5.0; // NTU
}

float readTDS() {
  int raw = analogRead(TDS_PIN);
  return (raw / 4095.0) * 1000.0; // ppm
}

void loop() {
  float ph = readPH();
  float temp = readTemp();
  float turb = readTurbidity();
  float tds = readTDS();

  // Send data in CSV format: sensor_id,ph,temp,turb,tds
  Serial.print(SENSOR_ID);
  Serial.print(",");
  Serial.print(ph, 2);
  Serial.print(",");
  Serial.print(temp, 2);
  Serial.print(",");
  Serial.print(turb, 2);
  Serial.print(",");
  Serial.println(tds, 2);

  delay(5000); // Send data every 5 seconds
}
