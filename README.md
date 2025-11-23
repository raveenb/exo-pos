# Exo-Pos: Posture Monitoring System

A wearable hat-mounted device that monitors head position and alerts users when poor posture is detected. Designed to help prevent "tech neck" and forward head posture with **bidirectional detection** for both forward and backward head tilt.

## Overview

This project uses an MPU6050/MPU9250 motion sensor mounted on a hat to track head position in real-time. When the user maintains poor posture for more than 5 seconds, an audio alert reminds them to correct their position.

### Key Features

- **Bidirectional head tilt detection** - Monitors both forward AND backward head movements
- **Real-time 3D visualization** - Live matplotlib display of head orientation
- **Auto-calibration** on startup for personalized neutral position
- **Smart alerting** with time-based filtering (5-second hold) and hysteresis
- **Movement detection** - Only alerts during static slouching, not active movement
- **JSON data output** for future app integration
- **Configurable thresholds** for different sensitivity levels
- **±90° detection range** for full head movement tracking

## Hardware Requirements

- Arduino Uno or compatible board
- MPU6050 or MPU9250 6/9-axis accelerometer/gyroscope module
- Active buzzer (connected to pin 13)
- USB cable for power and data
- Hat or headband for sensor mounting

### Bill of Materials

| Item | Quantity | Est. Cost |
|------|----------|-----------|
| Arduino Uno | 1 | $5-10 |
| MPU6050/MPU9250 Module | 1 | $1-3 |
| Active Buzzer | 1 | $0.50-1 |
| USB Cable | 1 | $2-5 |
| Hat/Headband | 1 | $5-10 |
| Jumper Wires | 4 | $1 |
| **Total** | | **~$15-30** |

### Wiring

```
MPU6050/MPU9250 → Arduino
VCC             → 5V
GND             → GND
SDA             → A4 (SDA)
SCL             → A5 (SCL)

Active Buzzer   → Arduino
+               → Pin 13
-               → GND
```

**Note**: Pin 13 has a built-in LED that will blink with the buzzer.

## Software Setup

### Prerequisites

**Arduino Firmware:**
- [Arduino IDE](https://www.arduino.cc/en/software) (version 1.8.0 or higher)
- Wire library (included with Arduino IDE)

**Python Visualizer (Optional):**
- Python 3.9 or higher (required by matplotlib 3.10+)
- pip (Python package manager)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/exo-pos.git
   cd exo-pos
   ```

2. **Upload Arduino Firmware:**
   - Open `arduino/posture_monitor_v3/posture_monitor_v3.ino` in Arduino IDE
   - Select your board: **Tools → Board → Arduino Uno** (or your board type)
   - Select the correct port: **Tools → Port → /dev/ttyUSB0** (or your port)
   - Upload the sketch: **Sketch → Upload** (or Ctrl+U)

3. **Install Python Visualizer (Optional):**
   ```bash
   # Create virtual environment (recommended)
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies
   pip install pyserial matplotlib numpy
   ```

### Configuration

All adjustable parameters are at the top of `posture_monitor_v3.ino`:

```cpp
// Detection sensitivity (bidirectional - both forward and backward tilt)
const float FORWARD_SLOUCH_ANGLE = 15.0;   // Degrees from neutral (±15°)
const float HYSTERESIS = 2.0;              // Deadband to prevent flickering
const float SIDE_TILT_ANGLE = 20.0;        // Left/right tilt threshold

// Timing
const unsigned long SLOUCH_HOLD_MS = 5000;        // 5s hold before alert
const unsigned long MOVEMENT_THRESHOLD = 20.0;    // Gyro threshold (°/s)

// Calibration
const unsigned long CALIBRATION_COUNTDOWN_MS = 10000;  // 10s countdown
```

## Usage

### Mounting

1. **Position the sensor** on top of a hat or headband
2. **Orient the sensor** so that:
   - The sensor board is parallel to the ground when you have good posture
   - The I2C pins face forward or backward (not sideways)
3. **Secure with tape** or hot glue
4. **Route the USB cable** comfortably down the back

**Note**: The firmware auto-detects sensor orientation and inverts axes as needed.

### Calibration

1. **Put on the hat** and sit with good posture (back straight, head aligned)
2. **Power on the device** (plug in USB)
3. **Wait for 3 beeps** - this signals calibration is starting
4. **Hold perfectly still for 10 seconds** during the countdown
5. **Listen for the completion beep** - calibration is done!

The device will print: `{"status":"calibrated","pitch_offset":...,"roll_offset":...}`

### Monitoring Options

**Option 1: Serial Monitor (Text Output)**

Open the Serial Monitor (**Tools → Serial Monitor**) at **115200 baud** to see real-time JSON data:

```json
{"timestamp":5420,"pitch":0.5,"roll":1.2,"gyro_mag":2.3,"slouch":false,"alert_active":false,"cumulative_slouch_s":0.0}
```

**Option 2: 3D Visualizer (Recommended)**

Run the Python visualizer for a live 3D representation of your head orientation:

```bash
# Activate virtual environment if using one
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the visualizer - it will auto-detect and let you select the serial port
python3 scripts/visualize_orientation.py

# Or specify a serial port directly
python3 scripts/visualize_orientation.py /dev/ttyUSB0

# Or use environment variable
SERIAL_PORT=/dev/ttyUSB0 python3 scripts/visualize_orientation.py
```

**Port Selection:**
- **No arguments**: Visualizer will auto-detect all available serial ports and show an interactive menu
- **If only one port found**: Automatically selects it
- **Multiple ports**: Shows a numbered menu with descriptions to help you choose the correct Arduino
- **Command line argument**: `python3 scripts/visualize_orientation.py /dev/ttyUSB0` (overrides auto-detection)
- **Environment variable**: `SERIAL_PORT=/dev/cu.usbmodem1234` (overrides auto-detection)

The visualizer shows:
- **3D head model** with real-time orientation
- **2D top-down view** with slouch zones (red = bad posture, green = good)
- **Live data** including pitch, roll, gyroscope magnitude
- **Slouch detection status** and cumulative slouch time

**Data Fields**:
- `timestamp`: Milliseconds since startup
- `pitch`: Calibrated pitch angle (0° = neutral, positive = forward, negative = backward)
- `roll`: Calibrated roll angle (0° = neutral, positive = right, negative = left)
- `gyro_mag`: Gyroscope magnitude (°/s) - detects active head movement
- `slouch`: Boolean indicating bad posture detected (true = slouching)
- `alert_active`: Boolean indicating buzzer is currently beeping
- `cumulative_slouch_s`: Total time spent slouching in current session (seconds)

### Alert Behavior

1. **Good Posture**: No alerts, continuous monitoring
2. **Slouch Detected**: 5-second grace period begins
3. **Movement Check**: Alert only triggers if gyroscope magnitude < 20°/s (static slouch, not active movement)
4. **Alert Triggered**: Continuous beep after 5 seconds of static poor posture
5. **Alert Stops When**:
   - Posture improves to within ±13° of neutral (15° threshold - 2° hysteresis)
   - User starts moving (gyro magnitude > 20°/s)
6. **Cumulative Timer**: Tracks total slouch time across the session (resets only on device restart)

## Project Structure

```
exo-pos/
├── arduino/
│   ├── posture_monitor_v3/
│   │   └── posture_monitor_v3.ino  # Current firmware (use this!)
│   ├── try-1.ino                   # Original prototype (v1)
│   ├── posture_monitor_v2.ino      # Neck-mounted version (v2)
│   └── bluetooth_versions/         # Bluetooth experimental firmware
├── scripts/
│   ├── visualize_orientation.py    # 3D real-time visualizer
│   └── calibration_window.py       # Calibration helper tool
├── ARCHITECTURE.md                 # System architecture & roadmap
├── CLAUDE.md                       # Project instructions for AI
├── README.md                       # This file
└── .gitignore                      # Git ignore rules
```

## Troubleshooting

### Device always thinks I'm slouching

**Cause**: Calibration captured bad posture as neutral.

**Fix**:
1. Put on the hat and sit up straight with good posture
2. Reset Arduino (press reset button or re-plug USB)
3. Wait for 3 beeps, then hold perfectly still for 10 seconds during calibration
4. Listen for completion beep

### Backward tilt doesn't trigger alerts (forward tilt works)

**Cause**: You may be using an older firmware version (v2 or earlier).

**Fix**: Make sure you're using `posture_monitor_v3.ino` which includes bidirectional detection with the `fabs()` fix for both forward and backward tilt.

### Too sensitive / not sensitive enough

**Cause**: Threshold doesn't match your natural range of motion.

**Fix**: Adjust `FORWARD_SLOUCH_ANGLE` in the code:
- Too sensitive (false alarms): Increase to `20.0` or `25.0`
- Not sensitive enough: Decrease to `10.0` or `12.0`

### Buzzer makes "pop-pop-pop" sound instead of continuous beep

**Cause**: This was a bug in v3 before the `fabs()` fix in buzzer shutoff logic.

**Fix**: Update to the latest `posture_monitor_v3.ino` which uses absolute value in both detection and shutoff logic.

### Visualizer won't start

**Common issues**:
- **Python version too old**: The visualizer requires Python 3.9+ (for matplotlib 3.10+). Check your version with `python3 --version`
  - If you have Python 3.7-3.8, you can use older dependencies: `pip install "matplotlib<3.9" "numpy<2.0" pyserial`
- **Port not found**: Update the serial port in the script or pass as argument
- **Permission denied**: On Linux, add your user to `dialout` group: `sudo usermod -a -G dialout $USER`
- **Missing dependencies**: Run `pip install pyserial matplotlib numpy`
- **Arduino IDE Serial Monitor open**: Close it first - only one program can access the serial port at a time

### Serial monitor shows no data

**Check**:
- Correct baud rate (115200)
- Correct port selected
- USB cable is data-capable (not charge-only)
- Arduino IDE Serial Monitor and Python visualizer aren't both trying to use the same port

## Roadmap

### Phase 1: Basic Wired System ✅ (Completed)
- [x] MPU6050/MPU9250 integration
- [x] **Bidirectional slouch detection** (forward AND backward tilt)
- [x] Buzzer alerts with hysteresis
- [x] JSON data output
- [x] Auto-calibration with countdown
- [x] Movement detection (gyroscope filtering)
- [x] 3D real-time visualization

### Phase 2: Data Collection & Analysis (Next)
- [ ] Python data logger script with CSV export
- [ ] Historical posture analysis dashboard
- [ ] Daily/weekly posture reports
- [ ] Posture score calculation

### Phase 3: Wireless Operation (In Progress)
- [x] Bluetooth HC-05 support (experimental)
- [x] Bluetooth BLE HM-10 support (experimental)
- [ ] Mobile app (React Native/Flutter)
- [ ] Battery power system with charging
- [ ] Custom PCB design
- [ ] 3D-printed enclosure

### Phase 4: Advanced Features (Future)
- [ ] Machine learning posture classification
- [ ] Multi-posture detection (side tilt detection enabled)
- [ ] Personalized threshold learning
- [ ] Social features (posture challenges)
- [ ] Health app integration (Apple Health, Google Fit)

## Technical Details

### Sensor Specifications

**MPU6050 & MPU9250:**
- **Axes**: 6-axis (MPU6050) or 9-axis (MPU9250) motion tracking
- **Accelerometer range**: ±2g (16384 LSB/g)
- **Gyroscope range**: ±250°/s (131 LSB/°/s)
- **Communication**: I2C (address 0x68)
- **Update rate**: 10 Hz (100ms intervals)
- **Voltage**: 3.3V-5V compatible

### Detection Algorithm

**V3 Bidirectional Algorithm:**

1. **Read raw sensor data** (X, Y, Z acceleration + gyroscope)
2. **Convert to angles** using `atan2()`:
   - Pitch: `atan2(ay, az) * 180/π` (forward/backward tilt)
   - Roll: `atan2(ax, az) * 180/π` (left/right tilt)
3. **Apply calibration offset** (subtract neutral position captured during startup)
4. **Invert axes** for upside-down sensor mounting on hat
5. **Calculate gyroscope magnitude** to detect active head movement
6. **Check posture** using `fabs(pitch)` for bidirectional detection:
   - Forward slouch: pitch > +15°
   - Backward tilt: pitch < -15°
7. **Movement filtering**: Only alert if gyro magnitude < 20°/s (static slouch)
8. **Time-based filtering**: Must hold for 5 seconds before alert
9. **Hysteresis**: Alert clears when `fabs(pitch)` < 13° (15° - 2° hysteresis)
10. **Cumulative tracking**: Total slouch time tracked across entire session

### Why Hat-Mounted (V3)?

**Advantages over neck-mounted (V2):**
- **No skin contact** - more comfortable for extended wear
- **Easy to put on/take off** - just wear a hat
- **No adhesive needed** - no skin irritation
- **Better for different body types** - doesn't depend on neck anatomy
- **Socially acceptable** - looks like a normal hat
- **Adjustable position** - can fine-tune sensor placement

**Trade-offs:**
- Requires wearing a hat indoors
- Slightly less direct measurement than C7 vertebrae placement

## Contributing

Contributions are welcome! Areas for improvement:

- **Hardware**: Better mounting solutions, custom PCB design, 3D-printed enclosure
- **Firmware**: Side tilt detection refinement, battery optimization, wireless protocols
- **Software**: Data logger with CSV export, web dashboard, historical analysis
- **Documentation**: Setup guides, video tutorials, multilingual support
- **Mobile**: iOS/Android app development
- **Research**: Machine learning for personalized posture classification

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

MIT License - feel free to use, modify, and distribute this project.

See LICENSE file for full details.

## Acknowledgments

- Inspired by ergonomic research on "tech neck" and forward head posture
- Built with Arduino Uno and MPU6050/MPU9250 sensors
- 3D visualization using matplotlib
- Developed with assistance from Claude Code

## Support

For issues, questions, or suggestions:
- **Open an issue** on GitHub for bugs or feature requests
- Check `ARCHITECTURE.md` for detailed system design
- See firmware comments for implementation details

---

**Version**: 3.0 (Bidirectional Detection)
**Last Updated**: 2025-11-23
**Status**: Active Development | Open Source
