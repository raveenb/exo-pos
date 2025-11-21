# HC-05 Bluetooth Setup Guide

## Great News! HC-05 Requires ZERO Code Changes!

The HC-05 module acts as a **transparent serial bridge** - it's literally a wireless replacement for the USB cable. Your existing V3 firmware works as-is!

## Hardware Requirements

- HC-05 Bluetooth module
- **IMPORTANT**: 1kΩ and 2kΩ resistors for voltage divider (HC-05 RX is 3.3V, Arduino TX is 5V)
- Or use a logic level shifter

## Wiring Diagram

```
HC-05          Arduino Uno
─────          ───────────
VCC      →     5V
GND      →     GND
TXD      →     RX (Pin 0) - Direct connection OK
RXD      →     TX (Pin 1) - MUST use voltage divider!
```

### Voltage Divider for RXD (CRITICAL!)

HC-05 RX pin is 3.3V tolerant. Arduino TX outputs 5V. You MUST reduce voltage:

```
Arduino Pin 1 (TX)
        |
        1kΩ
        |
        +--------→ HC-05 RXD
        |
        2kΩ
        |
       GND

Formula: 5V × (2kΩ / (1kΩ + 2kΩ)) = 3.33V  ✓
```

## Upload Procedure (IMPORTANT!)

Since HC-05 uses pins 0/1 (same as USB serial), you must:

1. **Wire HC-05 but leave RXD disconnected**
2. **Upload firmware via USB** (arduino-cli or IDE)
3. **After upload completes, connect HC-05 RXD** (with voltage divider)
4. **Disconnect USB cable**
5. **Power Arduino via battery or external 5V**

## Pairing with Computer

### macOS:
1. Open **System Settings → Bluetooth**
2. HC-05 should appear as "HC-05" or "HC-05-DevB"
3. Default PIN: `1234` or `0000`
4. After pairing, it appears as `/dev/cu.HC-05-DevB` (or similar)

### Linux:
```bash
# Scan for devices
bluetoothctl scan on

# Pair
bluetoothctl pair XX:XX:XX:XX:XX:XX
# Enter PIN: 1234

# Connect
bluetoothctl connect XX:XX:XX:XX:XX:XX

# Bind to serial port
sudo rfcomm bind /dev/rfcomm0 XX:XX:XX:XX:XX:XX
```

### Windows:
1. Settings → Bluetooth → Add Device
2. Select HC-05
3. Enter PIN: `1234`
4. Check Device Manager for COM port number (e.g., COM5)

## Using with Visualizer

### Option 1: Update Port in visualize_orientation.py

Change line 26:
```python
SERIAL_PORT = '/dev/cu.HC-05-DevB'  # Or your HC-05 port
```

### Option 2: Run with environment variable

```bash
# macOS/Linux
SERIAL_PORT=/dev/cu.HC-05-DevB ./scripts/visualize_orientation.py

# Or temporarily disable USE_SERIAL_PORT and read from log
```

## Power Consumption

**HC-05 Current Draw:**
- Paired and connected: ~30-50mA
- Searching/pairing: ~30mA
- Idle: ~8mA (can be reduced with AT commands)

**Total System:**
- Arduino Uno: ~50mA
- MPU9250: ~3.5mA
- HC-05: ~40mA (average)
- Buzzer (when beeping): ~30mA
- **Total: ~123mA** (without buzzer active)

**Battery Life Estimates:**
- 500mAh LiPo: ~4 hours
- 1000mAh LiPo: ~8 hours
- 2000mAh LiPo: ~16 hours

## Range

- **Line of sight**: ~10 meters (30 feet)
- **Through walls**: ~5 meters (15 feet)
- Class 2 Bluetooth

## Troubleshooting

### HC-05 not appearing in Bluetooth scan

1. Check power (LED should be blinking)
2. HC-05 might already be paired - unpair and try again
3. Try AT mode to reset (see Advanced section)

### Can't upload firmware

- Disconnect HC-05 RXD before uploading
- Or physically remove HC-05 module
- Upload, then reconnect

### No data in visualizer

1. Check port name: `ls /dev/cu.*` (macOS) or `ls /dev/rfcomm*` (Linux)
2. Verify HC-05 is connected (not just paired)
3. Check baud rate matches (115200)
4. Try `screen /dev/cu.HC-05-DevB 115200` to see raw data

### Garbled data

- Check voltage divider is correct
- Verify baud rate (HC-05 default is 38400, but we're using 115200)
- May need to configure HC-05 baud rate (see Advanced)

## Advanced: Configuring HC-05 with AT Commands

To change HC-05 settings (baud rate, name, PIN):

### Enter AT Mode:
1. Disconnect from Arduino
2. Hold button on HC-05 while powering on
3. LED should blink slowly (~2 sec intervals)
4. Connect to computer via USB-to-Serial adapter
5. Open serial terminal at **38400 baud**

### Useful AT Commands:
```
AT                    # Test (should respond "OK")
AT+NAME=ExoPos        # Change device name
AT+PSWD=1234          # Change PIN
AT+UART=115200,0,0    # Set baud rate to 115200
AT+ROLE=0             # Set as slave (default)
```

## Advantages of HC-05

✅ **No code changes** - uses hardware Serial
✅ **Transparent** - acts like a wire
✅ **Simple pairing** - standard Bluetooth
✅ **Widely compatible** - works with any Bluetooth device

## Disadvantages

❌ **Higher power** - ~40mA vs ~10mA for BLE
❌ **Shorter range** - ~10m vs ~50m for BLE
❌ **Pins 0/1** - conflicts with USB programming
❌ **Voltage divider** - extra components needed

## Recommended Next Steps

1. **Wire HC-05 with voltage divider**
2. **Upload existing V3 firmware** (disconnect RXD during upload)
3. **Pair HC-05 with computer**
4. **Update visualizer port**
5. **Test with battery power**

If this works well, you're done! If you need better battery life or range, consider the HM-10 BLE version (already created in `posture_monitor_v3_ble/`).

---

**Status**: Ready to wire and test
**Firmware**: Use existing `posture_monitor_v3.ino` (no changes!)
**Required**: Voltage divider (1kΩ + 2kΩ resistors)
