# Exo-Pos: Posture Monitoring System

A wearable neck-mounted device that monitors head position and alerts users when poor posture is detected. Designed to help prevent "tech neck" and forward head posture.

## Overview

This project uses an MPU6050 6-axis motion sensor mounted on the C7 vertebrae (base of neck) to track head position in real-time. When the user maintains poor posture for more than 3 seconds, an audio alert reminds them to correct their position.

### Key Features

- **Real-time head position tracking** (pitch, roll, yaw rate)
- **Auto-calibration** on startup for personalized neutral position
- **Smart alerting** with time-based filtering (3-second hold) and hysteresis
- **JSON data output** for future app integration
- **Configurable thresholds** for different sensitivity levels
- **Alert cooldown** to prevent excessive notifications

## Hardware Requirements

- Arduino Uno/Nano or compatible board
- MPU6050 6-axis accelerometer/gyroscope module
- Passive buzzer (connected to pin 3)
- USB cable for power and data
- Medical tape or skin-safe adhesive for mounting

### Bill of Materials

| Item | Quantity | Est. Cost |
|------|----------|-----------|
| Arduino Nano | 1 | $3-5 |
| MPU6050 Module | 1 | $1-2 |
| Passive Buzzer | 1 | $0.50 |
| USB Cable | 1 | $2 |
| Medical Tape | 1 roll | $5 |
| Jumper Wires | 4 | $1 |
| **Total** | | **~$15** |

### Wiring

```
MPU6050 → Arduino
VCC     → 5V
GND     → GND
SDA     → A4 (SDA)
SCL     → A5 (SCL)

Buzzer  → Arduino
+       → Pin 3
-       → GND
```

## Software Setup

### Prerequisites

- [Arduino IDE](https://www.arduino.cc/en/software) (version 1.8.0 or higher)
- Wire library (included with Arduino IDE)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/exo-pos.git
   cd exo-pos
   ```

2. Open `arduino/posture_monitor_v2.ino` in Arduino IDE

3. Select your board: **Tools → Board → Arduino Nano** (or your board type)

4. Select the correct port: **Tools → Port → /dev/ttyUSB0** (or your port)

5. Upload the sketch: **Sketch → Upload** (or Ctrl+U)

### Configuration

All adjustable parameters are at the top of `posture_monitor_v2.ino`:

```cpp
// Detection sensitivity
const float FORWARD_SLOUCH_ANGLE = 15.0;   // Degrees forward from neutral
const float HYSTERESIS = 2.0;              // Deadband to prevent flickering

// Timing
const unsigned long SLOUCH_HOLD_MS = 3000;        // 3s hold before alert
const unsigned long BUZZER_DURATION_MS = 500;     // Beep length
const unsigned long ALERT_COOLDOWN_MS = 5000;     // 5s between alerts
```

## Usage

### Mounting

1. Locate your **C7 vertebra** (the prominent bump at the base of your neck)
2. Clean and dry the skin
3. Attach the device securely with medical tape
4. Route the USB cable comfortably (down back or to side)

### Calibration

1. **Sit with good posture** (back straight, head aligned)
2. Power on the device (plug in USB)
3. **Hold still for 1 second** during auto-calibration
4. You'll see: `{"status":"calibrated","pitch_offset":...}`

### Monitoring

Open the Serial Monitor (**Tools → Serial Monitor**) at **115200 baud** to see real-time data:

```json
{"timestamp":5420,"pitch":0.5,"pitch_raw":-12.1,"roll":1.2,"yaw_rate":-0.15,"threshold":15.0,"forward_slouch":false,"alert_active":false,"alert_type":0}
```

**Fields**:
- `timestamp`: Milliseconds since startup
- `pitch`: Calibrated pitch angle (0° = neutral, positive = forward)
- `pitch_raw`: Raw sensor angle before calibration
- `roll`: Left/right tilt angle
- `yaw_rate`: Head rotation speed (degrees/second)
- `threshold`: Current slouch detection threshold
- `forward_slouch`: Boolean indicating bad posture detected
- `alert_active`: Boolean indicating buzzer is active
- `alert_type`: 0=none, 1=single beep, 2=double, 3=triple

### Alert Behavior

1. **Good Posture**: No alerts, continuous monitoring
2. **Slouch Detected**: 3-second grace period
3. **Alert Triggered**: Single beep (500ms) after 3 seconds
4. **Cooldown Period**: 5 seconds before next alert can trigger
5. **Posture Corrected**: Alert stops, timer resets

## Project Structure

```
exo-pos/
├── arduino/
│   ├── try-1.ino              # Original prototype
│   ├── posture_monitor_v2.ino # Current version (use this!)
│   ├── claude.md              # Code analysis of v1
│   └── BUGFIX_V2.md           # Bug fixes documentation
├── ARCHITECTURE.md            # System architecture & roadmap
├── README.md                  # This file
└── .gitignore                 # Git ignore rules
```

## Troubleshooting

### Device always thinks I'm slouching

**Cause**: Calibration captured bad posture as neutral.

**Fix**:
1. Sit up straight with good posture
2. Reset Arduino (press reset button or re-plug USB)
3. Hold still during 1-second calibration

### Too sensitive / not sensitive enough

**Cause**: Threshold doesn't match your natural range of motion.

**Fix**: Adjust `FORWARD_SLOUCH_ANGLE` in the code:
- Too sensitive (false alarms): Increase to `20.0` or `25.0`
- Not sensitive enough: Decrease to `10.0` or `12.0`

### Buzzer keeps beeping constantly

**Cause**: This was a bug in earlier versions (see `BUGFIX_V2.md`).

**Fix**: Make sure you're using `posture_monitor_v2.ino` with the cooldown mechanism.

### Serial monitor shows no data

**Check**:
- Correct baud rate (115200)
- Correct port selected
- USB cable is data-capable (not charge-only)

## Roadmap

### Phase 1: Basic Wired System ✅ (Current)
- [x] MPU6050 integration
- [x] Forward slouch detection
- [x] Buzzer alerts
- [x] JSON data output
- [x] Auto-calibration

### Phase 2: Data Collection & Visualization (Next)
- [ ] Python data logger script
- [ ] Real-time web dashboard
- [ ] Historical posture analysis
- [ ] CSV export

### Phase 3: Wireless Operation (Future)
- [ ] Bluetooth module integration
- [ ] Mobile app (React Native/Flutter)
- [ ] Battery power system
- [ ] Custom PCB design

### Phase 4: Advanced Features (Future)
- [ ] Machine learning posture classification
- [ ] Multi-posture detection (side tilt, rotation)
- [ ] Social features (posture challenges)
- [ ] Health app integration

## Technical Details

### Sensor Specifications

- **MPU6050**: 6-axis motion tracking (3-axis accel + 3-axis gyro)
- **Accelerometer range**: ±2g (16384 LSB/g)
- **Gyroscope range**: ±250°/s (131 LSB/°/s)
- **Communication**: I2C (address 0x68)
- **Update rate**: 10 Hz (100ms intervals)

### Detection Algorithm

1. **Read raw sensor data** (X, Y, Z acceleration)
2. **Convert to angles** using `atan2(ay, az)` for pitch
3. **Apply calibration offset** (subtract neutral position)
4. **Check threshold** (calibrated pitch > 15°)
5. **Time-based filtering** (must hold 3 seconds)
6. **Hysteresis** (must improve by 2° to clear alert)
7. **Cooldown** (5 seconds between alerts)

### Why C7 Vertebrae?

- **Consistent anatomical landmark** (easy to locate)
- **Directly measures neck angle** (C7 tilts forward with head)
- **Less hair interference** than higher neck positions
- **Comfortable** for extended wear

## Contributing

Contributions are welcome! Areas for improvement:

- Better mounting solutions (elastic band, collar clip)
- Enhanced calibration routine (multi-position)
- Data visualization scripts (Python/JavaScript)
- Mobile app development
- Custom PCB design
- 3D-printed enclosure

## License

MIT License - feel free to use, modify, and distribute this project.

## Acknowledgments

- Inspired by ergonomic research on "tech neck" and forward head posture
- Built with Arduino and MPU6050 sensor
- Developed with assistance from Claude Code

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check `ARCHITECTURE.md` for detailed system design
- See `BUGFIX_V2.md` for known issues and fixes

---

**Version**: 2.1
**Last Updated**: 2025-11-20
**Status**: Active Development
