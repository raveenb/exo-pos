/*
 * Posture Monitor V2 - C7 Vertebrae Mounted Head Position Tracker
 *
 * Hardware:
 *   - MPU6050 (accelerometer + gyroscope)
 *   - Buzzer on pin 3
 *   - Mounted on C7 vertebrae (base of neck)
 *
 * Features:
 *   - Multi-axis position tracking (pitch, roll, yaw rate)
 *   - Configurable alert patterns for different postures
 *   - Timestamped JSON output for future app integration
 *   - Calibration support (neutral position baseline)
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

// Gyroscope registers (measuring rotation rate) - for future use
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
// Positive value = head forward from neutral
const float FORWARD_SLOUCH_ANGLE = 15.0;   // Pitch threshold (degrees from neutral)
const float HYSTERESIS = 2.0;              // Deadband to prevent flickering

// Side tilt detection (optional - can be enabled later)
const float SIDE_TILT_ANGLE = 15.0;        // Roll threshold (degrees)
const bool ENABLE_SIDE_TILT_ALERT = false; // Currently disabled

// Timing thresholds
const unsigned long SLOUCH_HOLD_MS = 3000;  // Must maintain bad posture for 3s
const unsigned long BUZZER_DURATION_MS = 500; // Buzzer beep length

// Alert patterns
enum AlertPattern {
  ALERT_NONE = 0,
  ALERT_SINGLE_BEEP = 1,    // Forward slouch
  ALERT_DOUBLE_BEEP = 2,    // Side tilt (future)
  ALERT_TRIPLE_BEEP = 3     // Multiple issues (future)
};

// ============================================================================
// STATE VARIABLES
// ============================================================================

// Calibration offsets (neutral position)
float pitchOffset = 0.0;
float rollOffset = 0.0;

// Posture tracking
unsigned long slouchStartTime = 0;
bool buzzerActive = false;
unsigned long buzzerStartTime = 0;
unsigned long lastAlertTime = 0;  // Track last alert to prevent rapid retriggering
AlertPattern currentAlert = ALERT_NONE;

// Alert cooldown (prevent buzzer from retriggering immediately after finishing)
const unsigned long ALERT_COOLDOWN_MS = 5000;  // 5 seconds between alerts

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

// Read gyroscope (for future use - rotation rate)
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

// ============================================================================
// ALERT LOGIC
// ============================================================================

// Check if current posture requires alerting
bool checkPosture(float pitch, float roll) {
  bool forwardSlouch = (pitch > FORWARD_SLOUCH_ANGLE);
  bool sideTilt = ENABLE_SIDE_TILT_ALERT && (abs(roll) > SIDE_TILT_ANGLE);

  // Determine alert type
  if (forwardSlouch && sideTilt) {
    currentAlert = ALERT_TRIPLE_BEEP;
    return true;
  } else if (sideTilt) {
    currentAlert = ALERT_DOUBLE_BEEP;
    return true;
  } else if (forwardSlouch) {
    currentAlert = ALERT_SINGLE_BEEP;
    return true;
  } else {
    currentAlert = ALERT_NONE;
    return false;
  }
}

// Generate buzzer pattern based on alert type
void playAlertPattern(AlertPattern pattern) {
  unsigned long elapsed = millis() - buzzerStartTime;

  switch (pattern) {
    case ALERT_SINGLE_BEEP:
      // Single continuous beep
      digitalWrite(BUZZER_PIN, (elapsed < BUZZER_DURATION_MS) ? HIGH : LOW);
      if (elapsed >= BUZZER_DURATION_MS) {
        buzzerActive = false;
      }
      break;

    case ALERT_DOUBLE_BEEP:
      // Two short beeps: ON-OFF-ON-OFF
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
      break;

    case ALERT_TRIPLE_BEEP:
      // Three short beeps
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

void outputSerialPlotter(float pitch, float roll, float yawRate, bool alerting) {
  Serial.print("pitch:");
  Serial.print(pitch, 2);
  Serial.print(" roll:");
  Serial.print(roll, 2);
  Serial.print(" yaw_rate:");
  Serial.print(yawRate, 2);
  Serial.print(" threshold:");
  Serial.print(FORWARD_SLOUCH_ANGLE);
  Serial.print(" alert:");
  Serial.println(alerting ? 1 : 0);
}

void outputJSON(float pitch, float roll, float yawRate, bool alerting) {
  Serial.print("{");
  Serial.print("\"timestamp\":");
  Serial.print(millis());
  Serial.print(",\"pitch\":");
  Serial.print(pitch, 2);
  Serial.print(",\"pitch_raw\":");
  Serial.print(pitch + pitchOffset, 2);  // Show raw angle before calibration
  Serial.print(",\"roll\":");
  Serial.print(roll, 2);
  Serial.print(",\"yaw_rate\":");
  Serial.print(yawRate, 2);
  Serial.print(",\"threshold\":");
  Serial.print(FORWARD_SLOUCH_ANGLE, 1);
  Serial.print(",\"forward_slouch\":");
  Serial.print((pitch > FORWARD_SLOUCH_ANGLE) ? "true" : "false");
  Serial.print(",\"alert_active\":");
  Serial.print(alerting ? "true" : "false");
  Serial.print(",\"alert_type\":");
  Serial.print(currentAlert);
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

  Serial.println("{\"status\":\"initialized\",\"version\":\"v2\",\"device\":\"posture_monitor\"}");

  // Auto-calibrate on startup
  delay(1000);
  calibrate();
}

void loop() {
  unsigned long now = millis();

  // Read sensors
  float ax, ay, az;
  readAccelerometer(ax, ay, az);

  float gx, gy, gz;
  readGyroscope(gx, gy, gz);

  // Calculate posture angles
  float pitch, roll;
  calculatePosture(ax, ay, az, pitch, roll);

  // Yaw rate from gyroscope (head rotation speed)
  float yawRate = gz;  // degrees per second

  // Check if current posture is problematic
  bool inBadPosture = checkPosture(pitch, roll);

  // ---- TIME-BASED ALERT LOGIC ----
  if (inBadPosture) {
    // Start timing if this is a new slouch episode
    if (slouchStartTime == 0) {
      slouchStartTime = now;
    }

    // Trigger alert if held long enough AND cooldown period has passed
    if (!buzzerActive && (now - slouchStartTime >= SLOUCH_HOLD_MS)) {
      // Check if enough time has passed since last alert
      if (now - lastAlertTime >= ALERT_COOLDOWN_MS) {
        buzzerActive = true;
        buzzerStartTime = now;
        lastAlertTime = now;
      }
    }
  } else {
    // Reset timer when posture improves
    slouchStartTime = 0;
  }

  // ---- HYSTERESIS TURN-OFF ----
  // Only turn off buzzer if significantly better than threshold
  // (pitch must go BELOW threshold minus hysteresis)
  if (buzzerActive && !inBadPosture && pitch < (FORWARD_SLOUCH_ANGLE - HYSTERESIS)) {
    buzzerActive = false;
    digitalWrite(BUZZER_PIN, LOW);
  }

  // ---- BUZZER CONTROL ----
  if (buzzerActive) {
    playAlertPattern(currentAlert);
  }

  // ---- DATA OUTPUT ----
  if (outputMode == OUTPUT_JSON) {
    outputJSON(pitch, roll, yawRate, buzzerActive);
  } else {
    outputSerialPlotter(pitch, roll, yawRate, buzzerActive);
  }

  delay(100);  // 10 Hz update rate
}
