/*
 * Posture Monitor V3 - Progressive Alert System
 *
 * Hardware:
 *   - MPU6050 (accelerometer + gyroscope)
 *   - Buzzer on pin 3
 *   - Mounted on C7 vertebrae (base of neck)
 *
 * Features:
 *   - Multi-axis position tracking (pitch, roll, yaw rate)
 *   - Progressive alert escalation (5s, 30s, 1m, 2m, 3m, 4m, 5m)
 *   - Cumulative slouch time tracking (15-minute rolling window)
 *   - Motion detection to filter active movement vs static slouching
 *   - Positive feedback tone after correcting critical posture
 *   - Enhanced JSON output with detailed metrics
 */

#include <Wire.h>

// ============================================================================
// HARDWARE CONFIGURATION
// ============================================================================

// MPU6050 I2C address and registers
#define MPU_ADDR 0x68

// Accelerometer registers (measuring gravity direction)
#define ACCEL_XOUT_H 0x3B  // Roll axis (side tilt)
#define ACCEL_YOUT_H 0x3D  // Pitch axis (forward/back)
#define ACCEL_ZOUT_H 0x3F  // Vertical axis

// Gyroscope registers (measuring rotation rate)
#define GYRO_XOUT_H 0x43
#define GYRO_YOUT_H 0x45
#define GYRO_ZOUT_H 0x47

// Power management
#define PWR_MGMT_1   0x6B

// Buzzer
#define BUZZER_PIN 3

// ============================================================================
// POSTURE DETECTION PARAMETERS
// ============================================================================

// Forward head posture (tech neck) detection
// NOTE: This is RELATIVE to your calibrated neutral position
const float FORWARD_SLOUCH_ANGLE = 15.0;   // Pitch threshold (degrees from neutral)
const float HYSTERESIS = 2.0;              // Deadband to prevent flickering

// Side tilt detection (optional - can be enabled later)
const float SIDE_TILT_ANGLE = 15.0;        // Roll threshold (degrees)
const bool ENABLE_SIDE_TILT_ALERT = false; // Currently disabled

// Motion detection threshold
const float MOVEMENT_THRESHOLD = 20.0;     // deg/s - above this = active movement

// ============================================================================
// PROGRESSIVE ALERT SYSTEM
// ============================================================================

// Alert milestones (in milliseconds)
const unsigned long ALERT_MILESTONES[] = {
  5000,    // 5s  - Single beep (gentle reminder)
  30000,   // 30s - Double beep (stronger warning)
  60000,   // 1m  - Triple beep (urgent)
  120000,  // 2m  - Triple beep
  180000,  // 3m  - Triple beep
  240000,  // 4m  - Triple beep
  300000   // 5m  - Continuous beep (critical!)
};
const int NUM_MILESTONES = 7;

// Alert levels
enum AlertLevel {
  LEVEL_NONE = 0,
  LEVEL_GENTLE = 1,      // 5s - single beep
  LEVEL_WARNING = 2,     // 30s - double beep
  LEVEL_URGENT = 3,      // 1m+ - triple beep
  LEVEL_CRITICAL = 4     // 5m+ - continuous
};

// Cumulative tracking
const unsigned long CUMULATIVE_WINDOW = 900000;  // 15 minutes

// ============================================================================
// STATE VARIABLES
// ============================================================================

// Calibration offsets (neutral position)
float pitchOffset = 0.0;
float rollOffset = 0.0;

// Cumulative time tracking
unsigned long cumulativeSlouchTime = 0;  // Total slouch time in window
unsigned long lastUpdateTime = 0;        // For delta time calculation
int currentMilestoneIndex = -1;          // Current alert milestone
bool wasCritical = false;                // Track if we were in critical state

// Posture tracking
bool inBadPosture = false;
bool isMoving = false;

// Buzzer state
bool buzzerActive = false;
unsigned long buzzerStartTime = 0;
AlertLevel currentAlertLevel = LEVEL_NONE;

// Output mode selection
enum OutputMode {
  OUTPUT_SERIAL_PLOTTER,  // Arduino plotter format: "pitch:X roll:Y"
  OUTPUT_JSON             // Structured JSON for app parsing
};
OutputMode outputMode = OUTPUT_JSON;  // Default to JSON for future app

// ============================================================================
// SENSOR READING FUNCTIONS
// ============================================================================

// Read a 16-bit signed value from MPU6050 register
int16_t read16(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)2);
  int16_t high = Wire.read();
  int16_t low = Wire.read();
  return (high << 8) | low;
}

// Read all accelerometer axes
void readAccelerometer(float &ax, float &ay, float &az) {
  int16_t ax_raw = read16(ACCEL_XOUT_H);
  int16_t ay_raw = read16(ACCEL_YOUT_H);
  int16_t az_raw = read16(ACCEL_ZOUT_H);

  // Convert to g-forces (±2g range: 16384 LSB/g)
  ax = ax_raw / 16384.0;
  ay = ay_raw / 16384.0;
  az = az_raw / 16384.0;
}

// Read gyroscope (rotation rate)
void readGyroscope(float &gx, float &gy, float &gz) {
  int16_t gx_raw = read16(GYRO_XOUT_H);
  int16_t gy_raw = read16(GYRO_YOUT_H);
  int16_t gz_raw = read16(GYRO_ZOUT_H);

  // Convert to degrees/second (±250°/s range: 131 LSB/°/s)
  gx = gx_raw / 131.0;
  gy = gy_raw / 131.0;
  gz = gz_raw / 131.0;
}

// ============================================================================
// POSTURE CALCULATION
// ============================================================================

// Calculate head position angles from accelerometer
void calculatePosture(float ax, float ay, float az, float &pitch, float &roll) {
  // Pitch: forward/backward tilt (looking down/up)
  // When head goes forward, C7 tilts forward -> pitch increases
  pitch = atan2(ay, az) * 180.0 / PI;

  // Roll: left/right tilt (ear to shoulder)
  roll = atan2(ax, az) * 180.0 / PI;

  // Apply calibration offsets
  pitch -= pitchOffset;
  roll -= rollOffset;
}

// Check if user is actively moving (not static slouch)
bool checkMovement(float gx, float gy, float gz) {
  // Calculate magnitude of rotation
  float gyroMagnitude = sqrt(gx*gx + gy*gy + gz*gz);
  return (gyroMagnitude > MOVEMENT_THRESHOLD);
}

// Check if current posture requires alerting
bool checkPosture(float pitch, float roll) {
  bool forwardSlouch = (pitch > FORWARD_SLOUCH_ANGLE);
  bool sideTilt = ENABLE_SIDE_TILT_ALERT && (abs(roll) > SIDE_TILT_ANGLE);

  return (forwardSlouch || sideTilt);
}

// ============================================================================
// CUMULATIVE TIME TRACKING
// ============================================================================

void updateCumulativeTime(unsigned long deltaTime) {
  if (inBadPosture && !isMoving) {
    // Accumulate slouch time (only when static, not moving)
    cumulativeSlouchTime += deltaTime;

    // Cap at maximum window
    if (cumulativeSlouchTime > CUMULATIVE_WINDOW) {
      cumulativeSlouchTime = CUMULATIVE_WINDOW;
    }
  } else {
    // Gradually reduce cumulative time when in good posture
    // Decay rate: 1ms of good posture removes 1ms of accumulated slouch
    if (cumulativeSlouchTime >= deltaTime) {
      cumulativeSlouchTime -= deltaTime;
    } else {
      cumulativeSlouchTime = 0;
    }
  }
}

// Determine current alert level based on cumulative time
AlertLevel getCurrentAlertLevel() {
  if (cumulativeSlouchTime >= ALERT_MILESTONES[6]) {
    return LEVEL_CRITICAL;  // 5 minutes - continuous beep
  } else if (cumulativeSlouchTime >= ALERT_MILESTONES[2]) {
    return LEVEL_URGENT;    // 1+ minutes - triple beep
  } else if (cumulativeSlouchTime >= ALERT_MILESTONES[1]) {
    return LEVEL_WARNING;   // 30 seconds - double beep
  } else if (cumulativeSlouchTime >= ALERT_MILESTONES[0]) {
    return LEVEL_GENTLE;    // 5 seconds - single beep
  } else {
    return LEVEL_NONE;
  }
}

// Check if we've crossed a new milestone
bool shouldTriggerAlert() {
  AlertLevel newLevel = getCurrentAlertLevel();

  // Trigger alert if we've reached a new level
  if (newLevel > currentAlertLevel) {
    currentAlertLevel = newLevel;
    return true;
  }

  return false;
}

// ============================================================================
// ALERT PATTERNS
// ============================================================================

// Play single beep (gentle reminder)
void playSingleBeep() {
  unsigned long elapsed = millis() - buzzerStartTime;

  if (elapsed < 300) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else {
    digitalWrite(BUZZER_PIN, LOW);
    if (elapsed >= 400) buzzerActive = false;
  }
}

// Play double beep (warning)
void playDoubleBeep() {
  unsigned long elapsed = millis() - buzzerStartTime;

  if (elapsed < 200) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else if (elapsed < 300) {
    digitalWrite(BUZZER_PIN, LOW);
  } else if (elapsed < 500) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else {
    digitalWrite(BUZZER_PIN, LOW);
    if (elapsed >= 600) buzzerActive = false;
  }
}

// Play triple beep (urgent)
void playTripleBeep() {
  unsigned long elapsed = millis() - buzzerStartTime;

  if (elapsed < 150) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else if (elapsed < 200) {
    digitalWrite(BUZZER_PIN, LOW);
  } else if (elapsed < 350) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else if (elapsed < 400) {
    digitalWrite(BUZZER_PIN, LOW);
  } else if (elapsed < 550) {
    digitalWrite(BUZZER_PIN, HIGH);
  } else {
    digitalWrite(BUZZER_PIN, LOW);
    if (elapsed >= 650) buzzerActive = false;
  }
}

// Play continuous beep (critical - 5 minutes)
void playContinuousBeep() {
  unsigned long elapsed = millis() - buzzerStartTime;

  // Intermittent at first (1s on, 1s off) for 30 seconds
  if (elapsed < 30000) {
    int cycle = (elapsed / 1000) % 2;
    digitalWrite(BUZZER_PIN, cycle == 0 ? HIGH : LOW);
  } else {
    // Then continuous
    digitalWrite(BUZZER_PIN, HIGH);
  }

  // This continues until posture improves (no auto-stop)
}

// Play success tone (posture corrected after critical)
void playSuccessTone() {
  unsigned long elapsed = millis() - buzzerStartTime;

  // Ascending beep pattern: low-mid-high
  if (elapsed < 100) {
    tone(BUZZER_PIN, 500);  // Low
  } else if (elapsed < 200) {
    noTone(BUZZER_PIN);
  } else if (elapsed < 300) {
    tone(BUZZER_PIN, 800);  // Mid
  } else if (elapsed < 400) {
    noTone(BUZZER_PIN);
  } else if (elapsed < 500) {
    tone(BUZZER_PIN, 1200); // High
  } else {
    noTone(BUZZER_PIN);
    if (elapsed >= 600) buzzerActive = false;
  }
}

// Route to appropriate alert pattern
void playAlertPattern() {
  switch (currentAlertLevel) {
    case LEVEL_GENTLE:
      playSingleBeep();
      break;
    case LEVEL_WARNING:
      playDoubleBeep();
      break;
    case LEVEL_URGENT:
      playTripleBeep();
      break;
    case LEVEL_CRITICAL:
      playContinuousBeep();
      break;
    default:
      digitalWrite(BUZZER_PIN, LOW);
      buzzerActive = false;
      break;
  }
}

// ============================================================================
// OUTPUT FUNCTIONS
// ============================================================================

void outputSerialPlotter(float pitch, float roll, float yawRate) {
  Serial.print("pitch:");
  Serial.print(pitch, 2);
  Serial.print(" roll:");
  Serial.print(roll, 2);
  Serial.print(" cumulative_s:");
  Serial.print(cumulativeSlouchTime / 1000);
  Serial.print(" threshold:");
  Serial.print(FORWARD_SLOUCH_ANGLE);
  Serial.print(" alert_level:");
  Serial.println(currentAlertLevel);
}

void outputJSON(float pitch, float roll, float gx, float gy, float gz) {
  Serial.print("{");
  Serial.print("\"timestamp\":");
  Serial.print(millis());

  // Posture data
  Serial.print(",\"pitch\":");
  Serial.print(pitch, 2);
  Serial.print(",\"pitch_raw\":");
  Serial.print(pitch + pitchOffset, 2);
  Serial.print(",\"roll\":");
  Serial.print(roll, 2);

  // Movement data
  Serial.print(",\"gyro_x\":");
  Serial.print(gx, 2);
  Serial.print(",\"gyro_y\":");
  Serial.print(gy, 2);
  Serial.print(",\"gyro_z\":");
  Serial.print(gz, 2);
  Serial.print(",\"is_moving\":");
  Serial.print(isMoving ? "true" : "false");

  // Cumulative tracking
  Serial.print(",\"cumulative_slouch_ms\":");
  Serial.print(cumulativeSlouchTime);
  Serial.print(",\"cumulative_slouch_s\":");
  Serial.print(cumulativeSlouchTime / 1000);

  // Current milestone info
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

  // Alert state
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

  Serial.println("}");
}

// ============================================================================
// CALIBRATION
// ============================================================================

// Calibrate neutral position (run at startup or on command)
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

// ============================================================================
// SETUP & MAIN LOOP
// ============================================================================

void setup() {
  Serial.begin(115200);
  Wire.begin();

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // Wake up MPU6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(PWR_MGMT_1);
  Wire.write(0);  // Clear sleep bit
  Wire.endTransmission();

  delay(100);  // Let sensor stabilize

  Serial.println("{\"status\":\"initialized\",\"version\":\"v3\",\"device\":\"posture_monitor\"}");

  // Auto-calibrate on startup
  delay(1000);
  calibrate();

  // Initialize timing
  lastUpdateTime = millis();
}

void loop() {
  unsigned long now = millis();
  unsigned long deltaTime = now - lastUpdateTime;
  lastUpdateTime = now;

  // Read sensors
  float ax, ay, az;
  readAccelerometer(ax, ay, az);

  float gx, gy, gz;
  readGyroscope(gx, gy, gz);

  // Calculate posture angles
  float pitch, roll;
  calculatePosture(ax, ay, az, pitch, roll);

  // Check for movement
  isMoving = checkMovement(gx, gy, gz);

  // Check if current posture is problematic
  inBadPosture = checkPosture(pitch, roll);

  // Update cumulative slouch time
  updateCumulativeTime(deltaTime);

  // ---- ALERT LOGIC ----

  // Check if we should trigger a new alert (crossed milestone)
  if (shouldTriggerAlert() && !buzzerActive) {
    buzzerActive = true;
    buzzerStartTime = now;
  }

  // Handle posture correction after critical state
  if (wasCritical && currentAlertLevel < LEVEL_CRITICAL) {
    // User corrected posture after 5-minute continuous beep
    // Play success tone and aggressively reduce cumulative time
    buzzerActive = true;
    buzzerStartTime = now;
    currentAlertLevel = LEVEL_NONE;  // Temporarily set to play success tone
    cumulativeSlouchTime = cumulativeSlouchTime / 2;  // Remove 50% of accumulated time

    // Play success tone once
    playSuccessTone();
    wasCritical = false;
  }

  // Track if we're in critical state
  if (currentAlertLevel == LEVEL_CRITICAL) {
    wasCritical = true;
  }

  // Handle posture improvement (but not from critical)
  if (!inBadPosture && cumulativeSlouchTime < ALERT_MILESTONES[0]) {
    // Fully recovered - reset alert level
    currentAlertLevel = LEVEL_NONE;
    wasCritical = false;
  }

  // Stop non-critical alerts when posture improves significantly
  if (buzzerActive && currentAlertLevel != LEVEL_CRITICAL) {
    if (pitch < (FORWARD_SLOUCH_ANGLE - HYSTERESIS)) {
      buzzerActive = false;
      digitalWrite(BUZZER_PIN, LOW);
      noTone(BUZZER_PIN);
    }
  }

  // Stop critical alert only when posture is good
  if (buzzerActive && currentAlertLevel == LEVEL_CRITICAL) {
    if (!inBadPosture) {
      buzzerActive = false;
      digitalWrite(BUZZER_PIN, LOW);
    }
  }

  // ---- BUZZER CONTROL ----
  if (buzzerActive) {
    playAlertPattern();
  }

  // ---- DATA OUTPUT ----
  if (outputMode == OUTPUT_JSON) {
    outputJSON(pitch, roll, gx, gy, gz);
  } else {
    outputSerialPlotter(pitch, roll, gz);
  }

  delay(100);  // 10 Hz update rate
}
