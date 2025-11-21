# Bluetooth Upgrade Plan

## Goal
Make the posture monitor wireless by adding Bluetooth capability, enabling true wearable functionality.

## Hardware Options

### Option 1: HC-05/HC-06 (Classic Bluetooth) - EASIEST
**Pros:**
- Cheapest (~$5)
- Acts as transparent serial bridge (no code changes)
- Easy to pair with computer
- Drop-in replacement for USB serial

**Cons:**
- Higher power consumption (~30-50mA)
- Limited range (~10m)
- Not ideal for battery-powered wearable

**Wiring:**
```
HC-05     Arduino Uno
VCC   →   5V
GND   →   GND
TXD   →   RX (Pin 0)
RXD   →   TX (Pin 1)  (through voltage divider: 1kΩ + 2kΩ)
```

**Code Changes:** NONE! Just upload firmware, then disconnect USB and power via battery.

### Option 2: HM-10 (BLE) - BETTER FOR WEARABLE
**Pros:**
- Low power consumption (~8-10mA)
- Better range (~50m)
- Modern BLE protocol
- Good battery life

**Cons:**
- Slightly more expensive (~$10)
- Requires BLE-capable computer/phone
- Minor code changes needed (SoftwareSerial)

**Wiring:**
```
HM-10     Arduino Uno
VCC   →   5V
GND   →   GND
TXD   →   Pin 10 (Software Serial RX)
RXD   →   Pin 11 (Software Serial TX)
```

**Code Changes:** Use SoftwareSerial library for HM-10, keep hardware Serial for debugging.

### Option 3: ESP32 - BEST LONG-TERM ⭐
**Pros:**
- Built-in Bluetooth + WiFi
- Much more powerful (240MHz vs 16MHz)
- Same price as Arduino Uno (~$10)
- Better power management
- Can add web interface later
- Native USB support

**Cons:**
- Need to port code from Arduino to ESP32
- Different pin assignments
- 3.3V logic (vs 5V on Uno)

**Migration:**
- Replace Arduino Uno with ESP32 DevKit
- MPU9250 already supports 3.3V
- Rewrite using ESP32 Bluetooth Serial library

## Recommended Approach: Phased Migration

### Phase 1: Quick Test (HC-05) - **THIS WEEKEND**
1. Get HC-05 module
2. Wire to Arduino Uno
3. Test with existing firmware (no code changes!)
4. Update Python visualizer to connect via Bluetooth serial port
5. Verify range and battery life

### Phase 2: BLE Upgrade (HM-10) - **IF NEEDED**
1. Replace HC-05 with HM-10
2. Minimal code changes (SoftwareSerial)
3. Update Python visualizer for BLE

### Phase 3: ESP32 Migration - **FUTURE**
1. Port firmware to ESP32
2. Add WiFi logging
3. Create web dashboard
4. Mobile app integration

## Visualizer Changes Needed

The Python visualizer needs to connect to Bluetooth serial instead of USB serial.

### For Classic Bluetooth (HC-05):
- On macOS: `/dev/cu.HC-05-DevB` (or similar)
- On Linux: `/dev/rfcomm0`
- On Windows: `COM5` (or similar)

Just change the `SERIAL_PORT` in `visualize_orientation.py`!

### For BLE (HM-10):
Requires `bleak` library for BLE communication:
```bash
uv pip install bleak
```

## Power Considerations

### Current Draw:
- Arduino Uno: ~50mA
- MPU9250: ~3.5mA
- Buzzer (active): ~30mA (when beeping)
- HC-05: ~30-50mA
- **Total: ~133mA** (without buzzer beeping)

### Battery Options:
1. **3.7V LiPo 500mAh** - ~3-4 hours runtime
2. **3.7V LiPo 1000mAh** - ~7-8 hours runtime
3. **3.7V LiPo 2000mAh** - ~15 hours runtime (all day!)

Need to add:
- LiPo battery
- LiPo charger module (TP4056)
- Voltage regulator (if using 3.7V battery with 5V Uno)
- Power switch

## Next Steps

1. **Order hardware:**
   - HC-05 Bluetooth module (~$5)
   - 3.7V 2000mAh LiPo battery (~$10)
   - TP4056 charging module (~$2)
   - Power switch (~$1)

2. **Test current firmware with Bluetooth:**
   - Wire HC-05 to Arduino
   - Pair with computer
   - Update visualizer serial port
   - Test range

3. **Design enclosure:**
   - 3D print case for Arduino + battery + MPU9250
   - Velcro strap for neck mounting
   - Access to charging port

4. **Future enhancements:**
   - Migrate to ESP32
   - Add mobile app
   - Add haptic feedback (vibration motor)
   - Add OLED display for status

## Estimated Cost

**Minimal Bluetooth Setup:**
- HC-05 module: $5
- 2000mAh LiPo: $10
- TP4056 charger: $2
- Switch + wires: $3
- **Total: ~$20**

**ESP32 Complete Upgrade:**
- ESP32 DevKit: $10
- 2000mAh LiPo: $10
- TP4056 charger: $2
- Switch + wires: $3
- **Total: ~$25** (and you can repurpose the Arduino Uno)

## Timeline

- **Week 1**: Order parts, design wiring
- **Week 2**: Assemble and test Bluetooth
- **Week 3**: Design and 3D print enclosure
- **Week 4**: Real-world testing and refinement

---

**Status:** Planning Phase
**Next Action:** Order HC-05 module to test Bluetooth functionality
**Priority:** Medium (current USB version works fine for desk use)
