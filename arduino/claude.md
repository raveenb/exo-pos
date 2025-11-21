# Arduino Posture Monitor - Code Understanding

## Overview
This is a **posture-monitoring system** that uses an MPU6050 sensor to detect when someone is slouching and alerts them with a buzzer.

**File**: `try-1.ino`

## Hardware Components

### MPU6050 Sensor
- **Type**: 6-axis motion tracking device (accelerometer + gyroscope)
- **Communication**: I2C protocol
- **Address**: `0x68`
- **Registers Used**:
  - `0x3D` - Y-axis acceleration (high byte)
  - `0x3F` - Z-axis acceleration (high byte)
  - `0x6B` - Power management register

### Buzzer
- **Pin**: Digital pin 3
- **Function**: Audio alert for slouching detection

## Detection Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `TRIGGER_ANGLE` | -75° | Threshold for slouch detection |
| `HYSTERESIS` | 2° | Buffer to prevent flickering (-77° to turn off) |
| `SLOUCH_MS` | 3000ms | Required hold time before alert |

## Architecture

### Posture Monitor System
```
MPU6050 Sensor → I2C Communication → Arduino
                                        ↓
                          Tilt Calculation (atan2)
                                        ↓
                          State Machine Logic
                                        ↓
                    Time-based + Hysteresis Filtering
                                        ↓
                          Buzzer Control + Serial Output
```

### Key Design Patterns

1. **I2C Communication**: Uses Wire library to read accelerometer data
2. **Tilt Calculation**: Converts Y and Z acceleration into orientation angle using `atan2(ay, az)`
3. **Smart Triggering**: Dual-layer filtering system:
   - Time-based: 3-second continuous slouch required
   - Hysteresis: 2° buffer prevents rapid on/off cycling

## Code Structure

### Functions

#### `read16(uint8_t reg)` (lines 22-28)
Reads a 16-bit value from MPU6050 register.

**Implementation**:
- Begins I2C transmission to MPU6050
- Writes register address
- Requests 2 bytes
- Combines high and low bytes into signed 16-bit integer

```cpp
int16_t read16(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)2);
  return (Wire.read() << 8) | Wire.read();
}
```

#### `setup()` (lines 30-42)
Initializes hardware and communication.

**Steps**:
1. Start serial communication (115200 baud)
2. Initialize I2C bus
3. Configure buzzer pin as output (LOW)
4. Wake MPU6050 by writing 0 to power management register

#### `loop()` (lines 44-88)
Main execution loop running continuously.

**Process Flow**:
1. Read raw Y and Z acceleration values
2. Convert to g-forces (÷ 16384.0 for ±2g range)
3. Calculate tilt angle: `atan2(ay, az) * 180/π`
4. State machine logic:
   - **Slouching detected** → Start timer
   - **3 seconds elapsed** → Turn buzzer ON
   - **Upright posture** → Reset timer
   - **Past hysteresis threshold** → Turn buzzer OFF
5. Output telemetry to Serial Plotter
6. 120ms delay before next iteration

## State Machine Logic

### Slouch Detection (lines 62-70)
```cpp
if (inSlouch) {
  if (slouchStart == 0) slouchStart = now;  // Start timing
  if (!buzzerState && (now - slouchStart >= SLOUCH_MS)) {
    buzzerState = true;                      // Activate after 3s
    digitalWrite(BUZZER_PIN, HIGH);
  }
} else {
  slouchStart = 0;                           // Reset timer
}
```

### Hysteresis Turn-off (lines 72-76)
```cpp
if (buzzerState && tilt < (TRIGGER_ANGLE - HYSTERESIS)) {
  buzzerState = false;
  digitalWrite(BUZZER_PIN, LOW);
}
```

**Why Hysteresis?**
- Prevents "chattering" when user hovers at boundary
- Buzzer turns OFF at -77° (not -75°)
- Creates stable switching behavior

## Key Insights

### 1. Sensor Data Conversion
**Raw to Physical Units**:
- Raw values are 16-bit signed integers
- Division by 16384.0 assumes ±2g sensitivity mode (MPU6050 default)
- Formula: `acceleration_g = raw_value / 16384.0`

### 2. Tilt Calculation
**Why atan2(ay, az)?**
- Y-axis: forward/backward tilt
- Z-axis: up/down (gravity reference)
- `atan2()` gives angle relative to gravity vector
- Positive angle = leaning forward (slouching)

### 3. Debouncing Strategy
**Time-based Filtering**:
- Requires 3 continuous seconds of slouching
- Filters out temporary movements (reaching, adjusting)
- `slouchStart` timer resets immediately when posture improves

### 4. Serial Output Format
```
tilt:<angle> threshold:<value> buzzer:<0/1>
```
- Optimized for Arduino Serial Plotter
- Three data streams for visualization
- Real-time monitoring of system state

## Potential Improvements

### Robustness
1. **Explicit sensor configuration**: Set accelerometer range explicitly instead of assuming default
2. **Low-pass filtering**: Smooth noisy sensor data
3. **Error handling**: Check I2C communication success
4. **Calibration routine**: Allow user to set custom trigger angle

### Performance
1. **Non-blocking delays**: Replace `delay(120)` with timer-based approach
2. **Interrupt-driven I2C**: Could reduce polling overhead
3. **Variable sample rate**: Adjust based on activity level

### Features
1. **Battery monitoring**: If running on portable power
2. **Adjustable sensitivity**: Runtime configuration via serial commands
3. **Data logging**: Store posture history for analysis
4. **Multiple alerts**: Escalating buzzer patterns for prolonged slouching

## Technical Specifications

| Aspect | Details |
|--------|---------|
| Loop Rate | ~8 Hz (120ms delay) |
| Serial Baud | 115200 |
| I2C Speed | Standard (100 kHz, default) |
| Sensor Range | ±2g (assumed) |
| ADC Resolution | 16-bit |
| Sensitivity | 16384 LSB/g |

## References
- **MPU6050**: 6-axis MotionTracking device by InvenSense
- **Wire Library**: Arduino I2C communication library
- **atan2()**: Two-argument arctangent function for angle calculation
