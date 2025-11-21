#include <Wire.h>

// MPU6050 I2C address and registers
#define MPU_ADDR 0x68
#define ACCEL_YOUT_H 0x3D
#define ACCEL_ZOUT_H 0x3F
#define PWR_MGMT_1   0x6B

#define BUZZER_PIN 3

// Threshold logic (unchanged)
const float TRIGGER_ANGLE = -75.0;   // Start slouch zone (greater than -75)
const float HYSTERESIS = 2.0;        // To stop flickering

// Timing
const unsigned long SLOUCH_MS = 3000; // Must hold slouch for 3 seconds
bool buzzerState = false;

unsigned long slouchStart = 0;

// Read a 16-bit value from MPU
int16_t read16(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)2);
  return (Wire.read() << 8) | Wire.read();
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // Wake MPU
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(PWR_MGMT_1);
  Wire.write(0);
  Wire.endTransmission();
}

void loop() {

  // Read raw accel Y & Z
  int16_t ay_raw = read16(ACCEL_YOUT_H);
  int16_t az_raw = read16(ACCEL_ZOUT_H);

  float ay = ay_raw / 16384.0;
  float az = az_raw / 16384.0;

  // Compute tilt angle
  float tilt = atan2(ay, az) * 180.0 / PI;

  unsigned long now = millis();

  // Slouch condition (UNCHANGED)
  bool inSlouch = (tilt > TRIGGER_ANGLE);

  // ---- 3 SECOND HOLD LOGIC ----
  if (inSlouch) {
    if (slouchStart == 0) slouchStart = now; // Start timing slouch
    if (!buzzerState && (now - slouchStart >= SLOUCH_MS)) {
      buzzerState = true;
      digitalWrite(BUZZER_PIN, HIGH);
    }
  } else {
    slouchStart = 0;  // Reset hold timer
  }

  // ---- HYSTERESIS TURN-OFF ----
  if (buzzerState && tilt < (TRIGGER_ANGLE - HYSTERESIS)) {
    buzzerState = false;
    digitalWrite(BUZZER_PIN, LOW);
  }

  // ---- SERIAL PLOTTER OUTPUT ----
  // Format: tilt:<angle> threshold:<value> buzzer:<0/1>
  Serial.print("tilt:");
  Serial.print(tilt);
  Serial.print(" threshold:");
  Serial.print(TRIGGER_ANGLE);
  Serial.print(" buzzer:");
  Serial.println(buzzerState ? 1 : 0);

  delay(120);
}
