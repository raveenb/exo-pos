/*
 * Posture Monitor V3 - NO BUZZER VERSION
 *
 * This version has the buzzer completely disabled.
 * All alert logic still works and is logged, but no physical buzzer output.
 */

#include <Wire.h>

// MPU6050 I2C address and registers
#define MPU_ADDR 0x68
#define ACCEL_XOUT_H 0x3B
#define ACCEL_YOUT_H 0x3D
#define ACCEL_ZOUT_H 0x3F
#define GYRO_XOUT_H 0x43
#define GYRO_YOUT_H 0x45
#define GYRO_ZOUT_H 0x47
#define PWR_MGMT_1   0x6B

// Buzzer pin (not used, but defined for code compatibility)
#define BUZZER_PIN 3

// Posture detection parameters
const float FORWARD_SLOUCH_ANGLE = 15.0;
const float HYSTERESIS = 2.0;
const float SIDE_TILT_ANGLE = 15.0;
const bool ENABLE_SIDE_TILT_ALERT = false;
const float MOVEMENT_THRESHOLD = 20.0;

// Progressive alert milestones
const unsigned long ALERT_MILESTONES[] = {5000, 30000, 60000, 120000, 180000, 240000, 300000};
const int NUM_MILESTONES = 7;
const unsigned long CUMULATIVE_WINDOW = 900000;

enum AlertLevel {
  LEVEL_NONE = 0,
  LEVEL_GENTLE = 1,
  LEVEL_WARNING = 2,
  LEVEL_URGENT = 3,
  LEVEL_CRITICAL = 4
};

// State variables
float pitchOffset = 0.0;
float rollOffset = 0.0;
unsigned long cumulativeSlouchTime = 0;
unsigned long lastUpdateTime = 0;
int currentMilestoneIndex = -1;
bool wasCritical = false;
bool inBadPosture = false;
bool isMoving = false;
bool buzzerActive = false;
unsigned long buzzerStartTime = 0;
AlertLevel currentAlertLevel = LEVEL_NONE;

enum OutputMode {
  OUTPUT_SERIAL_PLOTTER,
  OUTPUT_JSON
};
OutputMode outputMode = OUTPUT_JSON;

// Sensor reading functions
int16_t read16(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)2);
  int16_t high = Wire.read();
  int16_t low = Wire.read();
  return (high << 8) | low;
}

void readAccelerometer(float &ax, float &ay, float &az) {
  int16_t ax_raw = read16(ACCEL_XOUT_H);
  int16_t ay_raw = read16(ACCEL_YOUT_H);
  int16_t az_raw = read16(ACCEL_ZOUT_H);
  ax = ax_raw / 16384.0;
  ay = ay_raw / 16384.0;
  az = az_raw / 16384.0;
}

void readGyroscope(float &gx, float &gy, float &gz) {
  int16_t gx_raw = read16(GYRO_XOUT_H);
  int16_t gy_raw = read16(GYRO_YOUT_H);
  int16_t gz_raw = read16(GYRO_ZOUT_H);
  gx = gx_raw / 131.0;
  gy = gy_raw / 131.0;
  gz = gz_raw / 131.0;
}

void calculatePosture(float ax, float ay, float az, float &pitch, float &roll) {
  pitch = atan2(ay, az) * 180.0 / PI;
  roll = atan2(ax, az) * 180.0 / PI;
  pitch -= pitchOffset;
  roll -= rollOffset;
}

bool checkMovement(float gx, float gy, float gz) {
  float gyroMagnitude = sqrt(gx*gx + gy*gy + gz*gz);
  return (gyroMagnitude > MOVEMENT_THRESHOLD);
}

bool checkPosture(float pitch, float roll) {
  bool forwardSlouch = (pitch > FORWARD_SLOUCH_ANGLE);
  bool sideTilt = ENABLE_SIDE_TILT_ALERT && (abs(roll) > SIDE_TILT_ANGLE);
  return (forwardSlouch || sideTilt);
}

void updateCumulativeTime(unsigned long deltaTime) {
  if (inBadPosture && !isMoving) {
    cumulativeSlouchTime += deltaTime;
    if (cumulativeSlouchTime > CUMULATIVE_WINDOW) {
      cumulativeSlouchTime = CUMULATIVE_WINDOW;
    }
  } else {
    if (cumulativeSlouchTime >= deltaTime) {
      cumulativeSlouchTime -= deltaTime;
    } else {
      cumulativeSlouchTime = 0;
    }
  }
}

AlertLevel getCurrentAlertLevel() {
  if (cumulativeSlouchTime >= ALERT_MILESTONES[6]) return LEVEL_CRITICAL;
  if (cumulativeSlouchTime >= ALERT_MILESTONES[2]) return LEVEL_URGENT;
  if (cumulativeSlouchTime >= ALERT_MILESTONES[1]) return LEVEL_WARNING;
  if (cumulativeSlouchTime >= ALERT_MILESTONES[0]) return LEVEL_GENTLE;
  return LEVEL_NONE;
}

bool shouldTriggerAlert() {
  AlertLevel newLevel = getCurrentAlertLevel();
  if (newLevel > currentAlertLevel) {
    currentAlertLevel = newLevel;
    return true;
  }
  return false;
}

void outputJSON(float pitch, float roll, float gx, float gy, float gz) {
  Serial.print("{");
  Serial.print("\"timestamp\":");
  Serial.print(millis());
  Serial.print(",\"pitch\":");
  Serial.print(pitch, 2);
  Serial.print(",\"pitch_raw\":");
  Serial.print(pitch + pitchOffset, 2);
  Serial.print(",\"roll\":");
  Serial.print(roll, 2);
  Serial.print(",\"gyro_x\":");
  Serial.print(gx, 2);
  Serial.print(",\"gyro_y\":");
  Serial.print(gy, 2);
  Serial.print(",\"gyro_z\":");
  Serial.print(gz, 2);
  Serial.print(",\"is_moving\":");
  Serial.print(isMoving ? "true" : "false");
  Serial.print(",\"cumulative_slouch_ms\":");
  Serial.print(cumulativeSlouchTime);
  Serial.print(",\"cumulative_slouch_s\":");
  Serial.print(cumulativeSlouchTime / 1000);

  if (currentAlertLevel > LEVEL_NONE && currentAlertLevel < LEVEL_CRITICAL) {
    int milestoneIndex = (currentAlertLevel == LEVEL_GENTLE) ? 0 :
                         (currentAlertLevel == LEVEL_WARNING) ? 1 : 2;
    Serial.print(",\"current_milestone\":");
    Serial.print(ALERT_MILESTONES[milestoneIndex] / 1000);
    if (milestoneIndex + 1 < NUM_MILESTONES) {
      Serial.print(",\"next_milestone\":");
      Serial.print(ALERT_MILESTONES[milestoneIndex + 1] / 1000);
    }
  } else if (currentAlertLevel == LEVEL_CRITICAL) {
    Serial.print(",\"current_milestone\":300");
    Serial.print(",\"next_milestone\":null");
  }

  Serial.print(",\"threshold\":");
  Serial.print(FORWARD_SLOUCH_ANGLE, 1);
  Serial.print(",\"forward_slouch\":");
  Serial.print(inBadPosture ? "true" : "false");
  Serial.print(",\"alert_active\":");
  Serial.print(buzzerActive ? "true" : "false");
  Serial.print(",\"alert_level\":");
  Serial.print(currentAlertLevel);
  Serial.print(",\"alert_level_name\":\"");
  switch (currentAlertLevel) {
    case LEVEL_NONE: Serial.print("none"); break;
    case LEVEL_GENTLE: Serial.print("gentle"); break;
    case LEVEL_WARNING: Serial.print("warning"); break;
    case LEVEL_URGENT: Serial.print("urgent"); break;
    case LEVEL_CRITICAL: Serial.print("critical"); break;
  }
  Serial.print("\"");
  Serial.print(",\"buzzer_disabled\":true");
  Serial.println("}");
}

void calibrate() {
  const int samples = 50;
  float pitch_sum = 0;
  float roll_sum = 0;

  Serial.println("{\"status\":\"calibrating\",\"message\":\"Hold neutral position...\"}");

  for (int i = 0; i < samples; i++) {
    float ax, ay, az;
    readAccelerometer(ax, ay, az);
    float pitch = atan2(ay, az) * 180.0 / PI;
    float roll = atan2(ax, az) * 180.0 / PI;
    pitch_sum += pitch;
    roll_sum += roll;
    delay(20);
  }

  pitchOffset = pitch_sum / samples;
  rollOffset = roll_sum / samples;

  Serial.print("{\"status\":\"calibrated\",\"pitch_offset\":");
  Serial.print(pitchOffset, 2);
  Serial.print(",\"roll_offset\":");
  Serial.print(rollOffset, 2);
  Serial.println("}");
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Set buzzer pin to INPUT to completely disconnect it
  pinMode(BUZZER_PIN, INPUT);

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(PWR_MGMT_1);
  Wire.write(0);
  Wire.endTransmission();

  delay(100);

  Serial.println("{\"status\":\"initialized\",\"version\":\"v3_no_buzzer\",\"device\":\"posture_monitor\",\"buzzer\":\"disabled\"}");

  delay(1000);
  calibrate();

  lastUpdateTime = millis();
}

void loop() {
  unsigned long now = millis();
  unsigned long deltaTime = now - lastUpdateTime;
  lastUpdateTime = now;

  float ax, ay, az;
  readAccelerometer(ax, ay, az);

  float gx, gy, gz;
  readGyroscope(gx, gy, gz);

  float pitch, roll;
  calculatePosture(ax, ay, az, pitch, roll);

  isMoving = checkMovement(gx, gy, gz);
  inBadPosture = checkPosture(pitch, roll);

  updateCumulativeTime(deltaTime);

  // Alert logic still runs (for logging) but no physical buzzer
  if (shouldTriggerAlert() && !buzzerActive) {
    buzzerActive = true;
    buzzerStartTime = now;
  }

  if (wasCritical && currentAlertLevel < LEVEL_CRITICAL) {
    buzzerActive = true;
    buzzerStartTime = now;
    currentAlertLevel = LEVEL_NONE;
    cumulativeSlouchTime = cumulativeSlouchTime / 2;
    wasCritical = false;
  }

  if (currentAlertLevel == LEVEL_CRITICAL) {
    wasCritical = true;
  }

  if (!inBadPosture && cumulativeSlouchTime < ALERT_MILESTONES[0]) {
    currentAlertLevel = LEVEL_NONE;
    wasCritical = false;
  }

  if (buzzerActive && currentAlertLevel != LEVEL_CRITICAL) {
    if (pitch < (FORWARD_SLOUCH_ANGLE - HYSTERESIS)) {
      buzzerActive = false;
    }
  }

  if (buzzerActive && currentAlertLevel == LEVEL_CRITICAL) {
    if (!inBadPosture) {
      buzzerActive = false;
    }
  }

  // NO BUZZER OUTPUT - completely disabled

  outputJSON(pitch, roll, gx, gy, gz);

  delay(100);
}
