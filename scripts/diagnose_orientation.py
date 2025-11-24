#!/usr/bin/env python3
"""
Diagnostic tool to determine sensor orientation after hardware configuration change.
This script displays live pitch/roll values to help identify which direction is forward/backward tilt.
"""

import json
import time
import sys
import serial as pyserial

# Serial configuration
BAUD_RATE = 115200

def find_arduino_port():
    """Auto-detect Arduino serial port"""
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())

        # Look for Arduino-like devices
        for port in ports:
            if 'usb' in port.device.lower() or 'acm' in port.device.lower():
                return port.device

        # If no obvious Arduino found, return first available port
        if ports:
            return ports[0].device
    except ImportError:
        pass

    # Fallback defaults
    return '/dev/cu.usbmodem212401' if sys.platform == 'darwin' else '/dev/ttyUSB0'

def main():
    # Get serial port
    if len(sys.argv) > 1:
        serial_port = sys.argv[1]
    else:
        serial_port = find_arduino_port()

    print(f"\n{'='*70}")
    print("SENSOR ORIENTATION DIAGNOSTIC TOOL")
    print(f"{'='*70}")
    print(f"Connecting to: {serial_port}")
    print(f"Baud rate: {BAUD_RATE}")
    print()

    try:
        ser = pyserial.Serial(serial_port, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize

        print("✓ Connected successfully!")
        print()
        print("INSTRUCTIONS:")
        print("1. Start with your head in NEUTRAL position (good posture)")
        print("2. Note the pitch and roll values")
        print("3. TILT HEAD FORWARD (slouch) - watch which values change")
        print("4. Return to NEUTRAL")
        print("5. TILT HEAD BACKWARD - watch which values change")
        print("6. Press Ctrl+C to exit")
        print()
        print(f"{'Time':<12} {'Pitch (cal)':<14} {'Pitch (raw)':<14} {'Roll (cal)':<14} {'Roll (raw)':<14}")
        print("-" * 70)

        # Clear any buffered data
        ser.reset_input_buffer()

        while True:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()

                if not line:
                    continue

                # Try to parse JSON
                try:
                    data = json.loads(line)

                    # Only show posture data
                    if 'pitch' in data and 'roll' in data:
                        timestamp = time.strftime('%H:%M:%S')
                        pitch_cal = data.get('pitch', 0.0)
                        pitch_raw = data.get('pitch_raw', 0.0)
                        roll_cal = data.get('roll', 0.0)
                        roll_raw = data.get('roll_raw', 0.0)

                        # Color code based on slouch status
                        slouch = data.get('slouch', False)
                        marker = "⚠ SLOUCH" if slouch else ""

                        print(f"{timestamp:<12} {pitch_cal:>+7.2f}°{'':<6} {pitch_raw:>+7.2f}°{'':<6} "
                              f"{roll_cal:>+7.2f}°{'':<6} {roll_raw:>+7.2f}°{'':<6} {marker}")

                except json.JSONDecodeError:
                    # Not JSON, might be debug message
                    if 'status' in line or 'debug' in line or 'error' in line:
                        print(f"[INFO] {line}")

            except KeyboardInterrupt:
                print("\n")
                print("="*70)
                print("ANALYSIS TIPS:")
                print("="*70)
                print("• If FORWARD tilt makes pitch MORE POSITIVE → orientation is correct")
                print("• If FORWARD tilt makes pitch MORE NEGATIVE → pitch axis is inverted")
                print("• If FORWARD tilt changes roll instead of pitch → axes are swapped")
                print("• Look at raw values vs calibrated values to understand the transformation")
                print()
                break

    except pyserial.SerialException as e:
        print(f"✗ Error connecting to {serial_port}: {e}")
        print()
        print("Available ports:")
        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                print(f"  - {port.device}: {port.description}")
        except ImportError:
            print("  (install pyserial to auto-detect ports)")
        return 1

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("✓ Serial connection closed")

    return 0

if __name__ == '__main__':
    sys.exit(main())
