#!/usr/bin/env python3
"""
Real-time Serial Monitor for Posture Monitor V3

Features:
- Reads JSON data from Arduino serial port
- Displays formatted output with color coding
- Logs to CSV file for later analysis
- Shows cumulative time and alert levels
"""

import serial
import json
import sys
import os
from datetime import datetime
import csv

# Configuration
SERIAL_PORT = '/dev/cu.usbmodem212401'
BAUD_RATE = 115200
LOG_FILE = 'posture_log.csv'

# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    ORANGE = '\033[38;5;214m'
    RED = '\033[91m'
    BRIGHT_RED = '\033[91;1m'
    BLUE = '\033[94m'
    GRAY = '\033[90m'

def get_alert_color(level_name):
    """Return color based on alert level"""
    colors = {
        'none': Colors.GREEN,
        'gentle': Colors.YELLOW,
        'warning': Colors.ORANGE,
        'urgent': Colors.RED,
        'critical': Colors.BRIGHT_RED
    }
    return colors.get(level_name, Colors.RESET)

def format_time(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}m {secs}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"

def display_posture_bar(pitch, threshold=15.0):
    """Display a visual bar showing posture deviation"""
    # Normalize pitch to 0-20 range for visualization
    normalized = max(0, min(20, pitch))
    bar_length = int(normalized)

    if pitch < threshold - 2:
        color = Colors.GREEN
        status = "GOOD"
    elif pitch < threshold:
        color = Colors.YELLOW
        status = "OK"
    elif pitch < threshold + 10:
        color = Colors.ORANGE
        status = "SLOUCH"
    else:
        color = Colors.RED
        status = "BAD"

    bar = "█" * bar_length + "░" * (20 - bar_length)
    return f"{color}{bar}{Colors.RESET} {status}"

def init_csv_log(filename):
    """Initialize CSV log file with headers"""
    file_exists = os.path.exists(filename)

    if not file_exists:
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'datetime', 'pitch', 'roll', 'cumulative_slouch_s',
                'is_moving', 'alert_level', 'alert_level_name', 'alert_active'
            ])
        print(f"{Colors.BLUE}📝 Created log file: {filename}{Colors.RESET}")
    else:
        print(f"{Colors.BLUE}📝 Appending to log file: {filename}{Colors.RESET}")

def log_to_csv(filename, data):
    """Append data to CSV log"""
    try:
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                data.get('timestamp', ''),
                datetime.now().isoformat(),
                data.get('pitch', ''),
                data.get('roll', ''),
                data.get('cumulative_slouch_s', ''),
                data.get('is_moving', ''),
                data.get('alert_level', ''),
                data.get('alert_level_name', ''),
                data.get('alert_active', '')
            ])
    except Exception as e:
        print(f"{Colors.RED}Error logging to CSV: {e}{Colors.RESET}")

def display_data(data):
    """Display formatted data to terminal"""
    # Status messages (calibration, etc.)
    if 'status' in data:
        status = data['status']
        if status == 'initialized':
            print(f"\n{Colors.BLUE}{'='*60}")
            print(f"🚀 Posture Monitor V3 Initialized")
            print(f"{'='*60}{Colors.RESET}\n")
        elif status == 'calibrating':
            print(f"{Colors.YELLOW}⏳ Calibrating... Hold neutral position!{Colors.RESET}")
        elif status == 'calibrated':
            print(f"{Colors.GREEN}✓ Calibration complete!")
            print(f"  Pitch offset: {data.get('pitch_offset', 'N/A'):.2f}°")
            print(f"  Roll offset:  {data.get('roll_offset', 'N/A'):.2f}°{Colors.RESET}\n")
        return

    # Main posture data
    if 'pitch' not in data:
        return

    pitch = data.get('pitch', 0)
    roll = data.get('roll', 0)
    cumulative_s = data.get('cumulative_slouch_s', 0)
    is_moving = data.get('is_moving', False)
    alert_level_name = data.get('alert_level_name', 'none')
    alert_active = data.get('alert_active', False)
    threshold = data.get('threshold', 15.0)

    # Get color based on alert level
    color = get_alert_color(alert_level_name)

    # Clear line and display compact status
    sys.stdout.write('\r' + ' ' * 120 + '\r')  # Clear line

    # Build status line
    posture_bar = display_posture_bar(pitch, threshold)
    movement_icon = "🏃" if is_moving else "🧍"
    alert_icon = "🔔" if alert_active else "  "

    status_line = (
        f"{alert_icon} "
        f"Pitch: {color}{pitch:+6.2f}°{Colors.RESET} | "
        f"Roll: {roll:+6.2f}° | "
        f"{movement_icon} | "
        f"Slouch: {color}{format_time(cumulative_s):>8}{Colors.RESET} | "
        f"{posture_bar} | "
        f"Alert: {color}{alert_level_name.upper():8}{Colors.RESET}"
    )

    sys.stdout.write(status_line)
    sys.stdout.flush()

    # Print newline on alert transitions
    if alert_active:
        print()  # New line when alert triggers
        print(f"{color}{'⚠️  '*10}{Colors.RESET}")
        print(f"{color}ALERT: {alert_level_name.upper()} - Cumulative slouch: {format_time(cumulative_s)}{Colors.RESET}")
        print(f"{color}{'⚠️  '*10}{Colors.RESET}")

def main():
    """Main serial monitor loop"""
    print(f"{Colors.BLUE}")
    print("=" * 60)
    print("  Posture Monitor V3 - Real-time Serial Monitor")
    print("=" * 60)
    print(f"{Colors.RESET}")
    print(f"📡 Connecting to {SERIAL_PORT} @ {BAUD_RATE} baud...")

    try:
        # Open serial connection
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"{Colors.GREEN}✓ Connected!{Colors.RESET}\n")

        # Initialize CSV log
        init_csv_log(LOG_FILE)

        print(f"{Colors.GRAY}Press Ctrl+C to stop{Colors.RESET}\n")

        # Read and display data
        while True:
            try:
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue

                # Try to parse as JSON
                try:
                    data = json.loads(line)
                    display_data(data)

                    # Log to CSV (only actual posture data, not status messages)
                    if 'pitch' in data:
                        log_to_csv(LOG_FILE, data)

                except json.JSONDecodeError:
                    # Not JSON, just print raw
                    print(f"{Colors.GRAY}{line}{Colors.RESET}")

            except UnicodeDecodeError:
                # Skip malformed data
                continue

    except serial.SerialException as e:
        print(f"{Colors.RED}❌ Serial error: {e}{Colors.RESET}")
        print(f"\nMake sure:")
        print(f"  1. Arduino is connected")
        print(f"  2. Correct port: {SERIAL_PORT}")
        print(f"  3. No other program is using the serial port")
        sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.BLUE}Monitoring stopped.{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Data logged to: {LOG_FILE}{Colors.RESET}")
        ser.close()
        sys.exit(0)

if __name__ == '__main__':
    main()
