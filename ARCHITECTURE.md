# Exo-Pos System Architecture
**Head Position Monitoring & Posture Correction System**

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CURRENT PHASE                            │
│                    (Wired, Real-time Alerting)                  │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │  MPU6050 Sensor  │ ← Mounted on C7 vertebrae
    │  - Accelerometer │   (base of neck)
    │  - Gyroscope     │
    └────────┬─────────┘
             │ I2C
             ↓
    ┌──────────────────┐
    │  Arduino Board   │
    │  - Sensor fusion │
    │  - Alert logic   │
    │  - Buzzer ctrl   │
    └────────┬─────────┘
             │ USB Serial (115200 baud)
             │ JSON output
             ↓
    ┌──────────────────┐
    │   Computer       │
    │  - Serial monitor│ ← Current: Manual monitoring
    │  - Data logging  │ ← Future: Automated collection
    └──────────────────┘

    ┌──────────────────┐
    │   Buzzer Alert   │ ← Local feedback
    └──────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────┐
│                         FUTURE PHASES                            │
│              (Wireless, App Integration, Analytics)             │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │  MPU6050 Sensor  │
    └────────┬─────────┘
             │ I2C
             ↓
    ┌──────────────────┐
    │  Arduino + BT    │ ← Add Bluetooth module (HC-05/BLE)
    │  - ESP32 or      │
    │  - Arduino Nano  │
    │    + HC-05       │
    └────────┬─────────┘
             │ Bluetooth
             ↓
    ┌──────────────────┐
    │  Mobile/Web App  │
    │  - Real-time viz │
    │  - Data logging  │
    │  - Config UI     │
    └────────┬─────────┘
             │ HTTP/WebSocket
             ↓
    ┌──────────────────┐
    │  Backend Server  │ ← Optional: Cloud storage
    │  - Time-series DB│
    │  - Analytics     │
    │  - Multi-device  │
    └────────┬─────────┘
             │
             ↓
    ┌──────────────────┐
    │  Data Viz Tools  │
    │  - Historical    │
    │  - Trends        │
    │  - Reports       │
    └──────────────────┘
```

## Hardware Components

### Current Implementation

| Component | Model | Function | Connection |
|-----------|-------|----------|------------|
| **Sensor** | MPU6050 | 6-axis motion tracking | I2C (SDA, SCL) |
| **Microcontroller** | Arduino Uno/Nano | Data processing & control | USB to computer |
| **Alert** | Passive buzzer | Audio feedback | Digital pin 3 |
| **Power** | USB 5V | Power supply | USB cable |
| **Mounting** | Medical tape/adhesive | Attach to C7 vertebrae | N/A |

### Future Hardware Additions

| Component | Purpose | Phase |
|-----------|---------|-------|
| **Bluetooth Module** | Wireless communication | Phase 2 |
| **Battery + Charging** | Portable operation | Phase 2 |
| **Custom PCB** | Compact, integrated design | Phase 3 |
| **Vibration Motor** | Silent alert option | Phase 3 |
| **LED Indicators** | Status feedback | Phase 3 |

## Software Architecture

### Layer 1: Embedded Firmware (Arduino)

**File**: `posture_monitor_v2.ino`

```
┌───────────────────────────────────────────────┐
│              ARDUINO FIRMWARE                  │
├───────────────────────────────────────────────┤
│                                               │
│  ┌──────────────────────────────────────┐   │
│  │   Sensor Interface Layer              │   │
│  │  - I2C communication                  │   │
│  │  - Raw data acquisition               │   │
│  │  - 16-bit register reads              │   │
│  └────────────────┬──────────────────────┘   │
│                   ↓                           │
│  ┌──────────────────────────────────────┐   │
│  │   Data Processing Layer               │   │
│  │  - Accelerometer → g-forces           │   │
│  │  - Gyroscope → degrees/sec            │   │
│  │  - Angle calculation (atan2)          │   │
│  │  - Calibration offset application     │   │
│  └────────────────┬──────────────────────┘   │
│                   ↓                           │
│  ┌──────────────────────────────────────┐   │
│  │   Posture Analysis Layer              │   │
│  │  - Threshold comparison               │   │
│  │  - Multi-axis evaluation              │   │
│  │  - Time-based filtering (3s hold)     │   │
│  │  - Hysteresis logic                   │   │
│  └────────────────┬──────────────────────┘   │
│                   ↓                           │
│  ┌──────────────────────────────────────┐   │
│  │   Alert Control Layer                 │   │
│  │  - Pattern generation                 │   │
│  │  - Buzzer timing                      │   │
│  │  - State machine                      │   │
│  └────────────────┬──────────────────────┘   │
│                   ↓                           │
│  ┌──────────────────────────────────────┐   │
│  │   Communication Layer                 │   │
│  │  - JSON serialization                 │   │
│  │  - Serial output (115200 baud)        │   │
│  │  - Timestamp generation               │   │
│  └───────────────────────────────────────┘   │
│                                               │
└───────────────────────────────────────────────┘
```

**Key Modules**:

1. **Sensor Interface** (`read16()`, `readAccelerometer()`, `readGyroscope()`)
   - Low-level I2C communication
   - Register reading and bit manipulation

2. **Posture Calculation** (`calculatePosture()`)
   - Pitch = atan2(ay, az) - forward/backward tilt
   - Roll = atan2(ax, az) - left/right tilt
   - Applies calibration offsets

3. **Alert Logic** (`checkPosture()`, `playAlertPattern()`)
   - Threshold-based detection
   - Time-based filtering (must hold 3 seconds)
   - Hysteresis to prevent flickering
   - Pattern generation for different alert types

4. **Data Output** (`outputJSON()`, `outputSerialPlotter()`)
   - Structured JSON for app parsing
   - Arduino plotter format for debugging

### Layer 2: Data Collection (Future)

**Options**:

#### Option A: Python Script (Simple)
```python
# serial_logger.py
import serial
import json
import sqlite3
from datetime import datetime

ser = serial.Serial('/dev/ttyUSB0', 115200)
db = sqlite3.connect('posture_data.db')

while True:
    line = ser.readline().decode('utf-8')
    data = json.loads(line)

    # Store to database
    db.execute('''
        INSERT INTO posture_logs
        (timestamp, pitch, roll, yaw_rate, alert_active)
        VALUES (?, ?, ?, ?, ?)
    ''', (datetime.now(), data['pitch'], data['roll'],
          data['yaw_rate'], data['alert_active']))
    db.commit()
```

#### Option B: Web Serial API (Browser-based)
```javascript
// web_monitor.html
const port = await navigator.serial.requestPort();
await port.open({ baudRate: 115200 });

const reader = port.readable.getReader();
while (true) {
  const { value, done } = await reader.read();
  if (done) break;

  const data = JSON.parse(new TextDecoder().decode(value));
  updateChart(data);  // Real-time visualization
  logToStorage(data); // Browser localStorage or IndexedDB
}
```

### Layer 3: Application Interface (Future)

```
┌─────────────────────────────────────────────────────┐
│                  APPLICATION LAYER                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │         Frontend (Mobile/Web)              │    │
│  │  ┌──────────────────────────────────────┐  │    │
│  │  │  Real-time Dashboard                 │  │    │
│  │  │  - Live posture visualization        │  │    │
│  │  │  - Current angles (pitch/roll)       │  │    │
│  │  │  - Alert status                      │  │    │
│  │  └──────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────┐  │    │
│  │  │  Historical View                     │  │    │
│  │  │  - Time-series charts                │  │    │
│  │  │  - Daily/weekly summaries            │  │    │
│  │  │  - Slouch frequency heatmap          │  │    │
│  │  └──────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────┐  │    │
│  │  │  Settings & Configuration            │  │    │
│  │  │  - Threshold adjustment              │  │    │
│  │  │  - Alert pattern selection           │  │    │
│  │  │  - Calibration control               │  │    │
│  │  └──────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │         Backend (Optional)                 │    │
│  │  - REST API for data access               │    │
│  │  - WebSocket for real-time streaming      │    │
│  │  - User authentication                     │    │
│  │  - Multi-device sync                       │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │         Database                           │    │
│  │  - Time-series storage (InfluxDB/SQLite)  │    │
│  │  - User profiles                           │    │
│  │  - Configuration settings                  │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Data Flow

### Current Implementation

```
MPU6050 → Arduino → USB Serial → Terminal
   ↓         ↓
Sensors   Processing
          & Buzzer
```

**Data Format** (JSON over Serial):
```json
{
  "timestamp": 5420,
  "pitch": -72.45,
  "roll": 3.21,
  "yaw_rate": -0.15,
  "forward_slouch": true,
  "alert_active": true,
  "alert_type": 1
}
```

**Update Rate**: 10 Hz (100ms intervals)

### Future Implementation (Wireless)

```
MPU6050 → Arduino → Bluetooth → Mobile App → Cloud
   ↓         ↓          ↓           ↓          ↓
Sensors   Processing  Wireless   Local UI   Analytics
          & Buzzer    Transfer   & Storage   & Backup
```

## Mounting Design

### C7 Vertebrae Placement

```
        HEAD (back view)
           ║
           ║  Neck
           ║
        ═══╬═══  ← C7 vertebra (prominent bump)
           ║
      ┌────┴────┐
      │ MPU6050 │  ← Sensor mounted here
      │  [PCB]  │     with medical adhesive
      └────┬────┘
           │
         Wire ↓
      (down back or to side)
```

**Orientation**:
- **X-axis**: Left/Right (perpendicular to spine)
- **Y-axis**: Forward/Backward (anterior/posterior)
- **Z-axis**: Up/Down (superior/inferior)

**When head goes forward** (tech neck):
- C7 tilts forward
- Y-acceleration increases (positive direction)
- Pitch angle increases above threshold (-75°)

### Enclosure Requirements

| Feature | Specification | Reason |
|---------|---------------|--------|
| **Size** | < 30mm × 30mm × 10mm | Minimal bulk on neck |
| **Weight** | < 20g | Prevent adhesive failure |
| **Edges** | Rounded, no sharp corners | Skin comfort |
| **Material** | Skin-safe plastic (ABS/PLA) | No irritation |
| **Cable** | Flexible, strain-relieved | Prevent detachment |
| **Adhesive** | Medical-grade tape | Safe, hypoallergenic |

## System States

```
┌──────────────┐
│  STARTUP     │
│  - Init I2C  │
│  - Wake MPU  │
└──────┬───────┘
       ↓
┌──────────────┐
│  CALIBRATING │ ← Auto-calibrate neutral position
│  - 50 samples│   (1 second)
│  - Calculate │
│    offsets   │
└──────┬───────┘
       ↓
┌──────────────┐
│  MONITORING  │ ← Main operational state
│  - Read data │   • Continuous sensor reading
│  - Analyze   │   • Posture evaluation
│  - Alert     │   • Output data stream
│  - Output    │
└──────┬───────┘
       ↓
       (loop back to MONITORING)
```

**Sub-states within MONITORING**:

1. **Good Posture**
   - No alert
   - Timer reset
   - Continuous monitoring

2. **Bad Posture Detected**
   - Start 3-second timer
   - No alert yet (grace period)

3. **Alert Active**
   - Buzzer pattern playing
   - Continues until posture improves

4. **Hysteresis Zone**
   - Posture improved but not enough to clear alert
   - Prevents rapid on/off cycling

## Configuration Parameters

### Adjustable via Serial Commands (Future)

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `FORWARD_SLOUCH_ANGLE` | -75° | -90° to -45° | Forward head threshold |
| `SIDE_TILT_ANGLE` | 15° | 5° to 30° | Lateral tilt threshold |
| `HYSTERESIS` | 2° | 1° to 5° | Deadband width |
| `SLOUCH_HOLD_MS` | 3000ms | 1000-10000ms | Alert delay |
| `BUZZER_DURATION_MS` | 500ms | 100-2000ms | Beep length |
| `OUTPUT_MODE` | JSON | JSON/Plotter | Data format |
| `ENABLE_SIDE_TILT_ALERT` | false | true/false | Side tilt detection |

## Development Phases

### ✅ Phase 1: Basic Wired System (CURRENT)
**Status**: Complete

- [x] MPU6050 integration
- [x] Forward slouch detection
- [x] Buzzer alerts
- [x] Serial output
- [x] Multi-axis tracking (pitch + roll)
- [x] JSON data format
- [x] Auto-calibration
- [x] Alert patterns framework

**Testing**:
- Mount on C7 with tape
- Verify angle changes with posture
- Confirm 3-second delay works
- Check buzzer activates correctly

### 🔄 Phase 2: Data Collection & Visualization
**Timeline**: Next iteration

- [ ] Python data logger script
- [ ] SQLite database storage
- [ ] Basic plotting (matplotlib/plotly)
- [ ] CSV export for analysis
- [ ] Real-time dashboard (web-based)

**Tools to Consider**:
- Python: `pyserial` + `pandas` + `plotly`
- Web: JavaScript + Chart.js + Web Serial API
- Desktop: Processing or Python/Tkinter GUI

### 🔮 Phase 3: Wireless Operation
**Timeline**: Future

- [ ] Bluetooth module integration (HC-05 or ESP32)
- [ ] Battery power system
- [ ] Mobile app (React Native / Flutter)
- [ ] Custom PCB design
- [ ] 3D-printed enclosure

### 🔮 Phase 4: Advanced Features
**Timeline**: Future

- [ ] Machine learning posture classification
- [ ] Predictive alerts (warn before bad posture)
- [ ] Multi-user profiles
- [ ] Social features (posture challenges)
- [ ] Integration with health apps

## Technology Stack

### Current
- **Hardware**: Arduino Uno/Nano, MPU6050, Passive Buzzer
- **Firmware**: Arduino C++ (Wire library)
- **Communication**: USB Serial (115200 baud)
- **Data Format**: JSON

### Proposed (Future Phases)

#### Option A: Web-Based (Cross-Platform)
```
Frontend:  HTML + JavaScript + Chart.js
Backend:   Node.js + Express + SQLite
Comms:     Web Serial API (Chrome/Edge)
Viz:       D3.js or Plotly.js
```

#### Option B: Native Mobile
```
Frontend:  React Native or Flutter
Backend:   Firebase or custom REST API
Comms:     Bluetooth Low Energy (BLE)
Storage:   SQLite on device
```

#### Option C: Desktop Application
```
Frontend:  Electron or Python/Tkinter
Backend:   Python + FastAPI
Comms:     PySerial
Storage:   SQLite or PostgreSQL
```

**Recommendation**: Start with **Option A** (web-based) because:
- No app store approval needed
- Works on any device with Chrome/Edge
- Easy to prototype and iterate
- Can add mobile PWA later

## Data Schema

### Time-Series Data
```sql
CREATE TABLE posture_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  device_millis INTEGER,  -- Arduino millis()
  pitch REAL,             -- degrees
  roll REAL,              -- degrees
  yaw_rate REAL,          -- degrees/sec
  forward_slouch BOOLEAN,
  side_tilt BOOLEAN,
  alert_active BOOLEAN,
  alert_type INTEGER
);

CREATE INDEX idx_timestamp ON posture_logs(timestamp);
```

### User Configuration
```sql
CREATE TABLE config (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Example rows:
-- ('forward_slouch_angle', '-75.0', ...)
-- ('slouch_hold_ms', '3000', ...)
```

### Calibration Data
```sql
CREATE TABLE calibrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  pitch_offset REAL,
  roll_offset REAL,
  notes TEXT
);
```

## Visualization Ideas

### Real-Time Dashboard
- **Gauge**: Current pitch/roll angles
- **Timeline**: Last 60 seconds of posture
- **Alert indicator**: Red/green status
- **Stats**: Alert count today

### Historical Analysis
- **Line chart**: Pitch over time (day/week/month)
- **Heatmap**: Hour-of-day slouch frequency
- **Bar chart**: Daily alert counts
- **Scatter plot**: Pitch vs roll distribution

### Reports
- **Daily summary**: Total time monitored, alerts triggered, worst periods
- **Weekly trends**: Improvement/degradation over time
- **Posture score**: Calculated metric (% time in good posture)

## Security & Privacy Considerations

### Current (Wired)
- ✅ No wireless transmission = no interception risk
- ✅ Local data only = no cloud privacy concerns

### Future (Wireless + App)
- Bluetooth: Pair with authentication
- Data storage: Encrypt sensitive health data
- Cloud sync: Optional, user-controlled
- Analytics: Anonymize before aggregation

## Bill of Materials (BOM)

### Current Prototype
| Item | Qty | Est. Cost | Source |
|------|-----|-----------|--------|
| Arduino Nano | 1 | $3-5 | AliExpress |
| MPU6050 Module | 1 | $1-2 | AliExpress |
| Passive Buzzer | 1 | $0.50 | AliExpress |
| USB Cable | 1 | $2 | Generic |
| Medical Tape | 1 roll | $5 | Pharmacy |
| Jumper Wires | 4 | $1 | Any electronics |
| **Total** | | **~$15** | |

### Future Wireless Version
Add:
| Item | Qty | Est. Cost |
|------|-----|-----------|
| ESP32 (replaces Arduino) | 1 | $5 |
| LiPo Battery (500mAh) | 1 | $5 |
| Charging module | 1 | $2 |
| Custom PCB | 1 | $10 (batch) |
| 3D-printed case | 1 | $2 (material) |
| **Additional Cost** | | **~$24** |

## Testing & Validation

### Unit Tests (Firmware)
- Sensor reading accuracy
- Angle calculation correctness
- Threshold logic
- Timing precision

### Integration Tests
- Serial communication reliability
- Buzzer pattern accuracy
- Calibration consistency

### User Acceptance Tests
- Comfort during 8-hour wear
- False positive rate
- False negative rate
- Battery life (future)

## Next Steps

### Immediate (This Week)
1. ✅ Complete V2 firmware
2. Test on actual C7 mounting
3. Collect baseline data
4. Refine threshold values

### Short-term (Next 2-4 Weeks)
1. Build Python data logger
2. Create basic visualization
3. Gather 1 week of continuous data
4. Analyze patterns

### Medium-term (1-3 Months)
1. Design web dashboard
2. Implement real-time charting
3. Add configuration UI
4. Test with multiple users

### Long-term (3-6 Months)
1. Bluetooth integration
2. Mobile app development
3. Custom PCB design
4. Beta testing program

## Resources & References

### Documentation
- [MPU6050 Datasheet](https://invensense.tdk.com/products/motion-tracking/6-axis/mpu-6050/)
- [Arduino Wire Library](https://www.arduino.cc/reference/en/language/functions/communication/wire/)
- [Web Serial API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API)

### Inspiration
- Posture tracking research papers
- Ergonomic best practices
- Wearable device design principles

### Communities
- Arduino forums
- r/arduino
- r/posture
- Maker communities

---

**Document Version**: 1.0
**Last Updated**: 2025-11-20
**Author**: System Architecture
**Status**: Living document - update as system evolves
