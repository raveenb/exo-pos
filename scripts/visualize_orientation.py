#!/Users/raveenbeemsingh/Developer/exo-pos/.venv/bin/python3
"""
Real-time 3D Orientation Visualizer for Posture Monitor

Reads JSON data from serial port and displays:
- 3D cube representing head orientation (pitch and roll)
- Real-time angle indicators
- Posture status and alerts
- Sensor mounted on hat for direct head tracking

Requirements:
    pip install matplotlib numpy pyserial
"""

import json
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from collections import deque

# Configuration
import os
import sys

def get_available_ports():
    """Get list of available serial ports"""
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        return [(p.device, f"{p.device} - {p.description}") for p in ports]
    except ImportError:
        return []

def select_serial_port():
    """Auto-detect available serial ports and let user select one"""
    try:
        import serial.tools.list_ports

        # Get list of available ports
        ports = list(serial.tools.list_ports.comports())

        if not ports:
            print("No serial ports found!")
            print("Please connect your Arduino and try again.")
            sys.exit(1)

        # If only one port, use it automatically
        if len(ports) == 1:
            selected_port = ports[0].device
            print(f"Auto-selected only available port: {selected_port}")
            print(f"  Description: {ports[0].description}")
            return selected_port

        # Multiple ports - show menu
        print("\nAvailable serial ports:")
        print("=" * 60)
        for i, port in enumerate(ports, 1):
            print(f"  [{i}] {port.device}")
            print(f"      Description: {port.description}")
            if port.manufacturer:
                print(f"      Manufacturer: {port.manufacturer}")
            print()

        # Get user selection
        while True:
            try:
                choice = input(f"Select port (1-{len(ports)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    print("Exiting.")
                    sys.exit(0)

                idx = int(choice) - 1
                if 0 <= idx < len(ports):
                    selected_port = ports[idx].device
                    print(f"\nSelected: {selected_port}")
                    return selected_port
                else:
                    print(f"Please enter a number between 1 and {len(ports)}")
            except (ValueError, KeyboardInterrupt):
                print("\nExiting.")
                sys.exit(0)

    except ImportError:
        print("Warning: serial.tools.list_ports not available")
        print("Please install pyserial: pip install pyserial")
        sys.exit(1)

# Serial port configuration
# Priority: 1) Command line arg  2) Environment variable  3) Auto-detect
if len(sys.argv) > 1:
    SERIAL_PORT = sys.argv[1]
    print(f"Using port from command line: {SERIAL_PORT}")
elif 'SERIAL_PORT' in os.environ:
    SERIAL_PORT = os.environ['SERIAL_PORT']
    print(f"Using port from environment: {SERIAL_PORT}")
else:
    print("No port specified, auto-detecting...")
    SERIAL_PORT = select_serial_port()

BAUD_RATE = 115200
SERIAL_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'serial.log')
UPDATE_INTERVAL = 100  # milliseconds

# Set to True to read from serial port directly, False to read from log file
USE_SERIAL_PORT = True

# Global state
current_data = {
    'pitch': 0,
    'roll': 0,
    'pitch_raw': 0,
    'forward_slouch': False,
    'alert_level_name': 'none',
    'cumulative_slouch_s': 0,
    'threshold': 15.0,
    'calibration_status': None,  # Track calibration state
    'calibration_countdown': None,  # Countdown timer
    'calibration_complete_time': None  # Time when calibration completed
}

# File/Serial tracking
log_file_handle = None
log_file_position = 0
serial_connection = None
current_serial_port = None  # Track which port is currently open
available_ports = []  # List of (device, description) tuples
port_selector_text = None  # Text widget showing current port

# Log message buffer (circular buffer for recent messages)
MAX_LOG_MESSAGES = 15  # Show last 15 messages
log_messages = deque(maxlen=MAX_LOG_MESSAGES)

def switch_serial_port(new_port):
    """Switch to a different serial port"""
    global serial_connection, current_serial_port, log_messages, smoothing_initialized

    # Close existing connection
    if serial_connection is not None:
        try:
            serial_connection.close()
            print(f"Closed connection to {current_serial_port}")
        except:
            pass
        serial_connection = None

    # Clear log and reset state
    log_messages.clear()
    smoothing_initialized = False

    # Open new connection
    try:
        import serial as pyserial
        serial_connection = pyserial.Serial(new_port, BAUD_RATE, timeout=0.1)
        current_serial_port = new_port
        log_messages.append(f"[{time.strftime('%H:%M:%S')}] STATUS: Connected to {new_port}")
        print(f"Connected to {new_port}")
    except Exception as e:
        log_messages.append(f"[{time.strftime('%H:%M:%S')}] ERROR: Failed to connect to {new_port}: {e}")
        print(f"Error connecting to {new_port}: {e}")

# Smoothing filter state (Exponential Moving Average)
smoothed_pitch = 0.0
smoothed_roll = 0.0
smoothing_initialized = False
SMOOTHING_ALPHA = 0.5  # Higher = more responsive, Lower = smoother (0.3-0.7 optimal)

# Debug: Print first few lines of serial data
serial_lines_printed = 0
MAX_DEBUG_LINES = 3  # Show first 3 data lines

def rotation_matrix_x(angle):
    """Rotation matrix around X axis (roll)"""
    rad = np.radians(angle)
    return np.array([
        [1, 0, 0],
        [0, np.cos(rad), -np.sin(rad)],
        [0, np.sin(rad), np.cos(rad)]
    ])

def rotation_matrix_y(angle):
    """Rotation matrix around Y axis (pitch)"""
    rad = np.radians(angle)
    return np.array([
        [np.cos(rad), 0, np.sin(rad)],
        [0, 1, 0],
        [-np.sin(rad), 0, np.cos(rad)]
    ])

def create_cube():
    """Create vertices for a cube representing the sensor"""
    # Define cube vertices (unit cube centered at origin)
    vertices = np.array([
        [-1, -1, -0.2],  # Bottom face (thinner)
        [1, -1, -0.2],
        [1, 1, -0.2],
        [-1, 1, -0.2],
        [-1, -1, 0.2],   # Top face
        [1, -1, 0.2],
        [1, 1, 0.2],
        [-1, 1, 0.2]
    ])

    # Define the 6 faces of the cube
    faces = [
        [vertices[0], vertices[1], vertices[5], vertices[4]],  # Front
        [vertices[2], vertices[3], vertices[7], vertices[6]],  # Back
        [vertices[0], vertices[3], vertices[7], vertices[4]],  # Left
        [vertices[1], vertices[2], vertices[6], vertices[5]],  # Right
        [vertices[4], vertices[5], vertices[6], vertices[7]],  # Top
        [vertices[0], vertices[1], vertices[2], vertices[3]]   # Bottom
    ]

    return faces

def rotate_cube(faces, pitch, roll):
    """Apply pitch and roll rotations to cube faces"""
    # Combine rotations: roll around X, then pitch around Y
    rot_x = rotation_matrix_x(roll)
    rot_y = rotation_matrix_y(pitch)
    combined_rotation = rot_y @ rot_x

    rotated_faces = []
    for face in faces:
        rotated_face = [combined_rotation @ vertex for vertex in face]
        rotated_faces.append(rotated_face)

    return rotated_faces

def get_alert_color(level_name):
    """Return color based on alert level"""
    colors = {
        'none': 'green',
        'gentle': 'yellow',
        'warning': 'orange',
        'urgent': 'red',
        'critical': 'darkred'
    }
    return colors.get(level_name, 'gray')

def add_log_message(line):
    """Add a message to the log buffer with timestamp"""
    timestamp = time.strftime('%H:%M:%S')

    # Try to parse as JSON and format nicely
    try:
        data = json.loads(line)
        if 'status' in data:
            msg = f"[{timestamp}] STATUS: {data.get('status')} - {data.get('message', '')}"
        elif 'debug' in data:
            msg = f"[{timestamp}] DEBUG: {data.get('debug')}"
        elif 'error' in data:
            msg = f"[{timestamp}] ERROR: {data.get('error')}"
        elif 'pitch' in data and 'roll' in data:
            # Don't log regular posture data
            return
        else:
            msg = f"[{timestamp}] {line[:60]}"
    except json.JSONDecodeError:
        # Non-JSON line
        msg = f"[{timestamp}] {line[:60]}"

    log_messages.append(msg)
    # Also print to console
    print(msg)

def read_latest_data():
    """Read data from serial port or log file"""
    global current_data, log_file_handle, log_file_position, serial_connection
    global smoothed_pitch, smoothed_roll, smoothing_initialized
    global serial_lines_printed, current_serial_port

    if USE_SERIAL_PORT:
        # Read directly from serial port
        try:
            import serial as pyserial

            # Open serial connection on first call
            if serial_connection is None:
                serial_connection = pyserial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
                current_serial_port = SERIAL_PORT
                print(f"Connected to {SERIAL_PORT} @ {BAUD_RATE} baud")
                print(f"\nShowing first {MAX_DEBUG_LINES} lines of serial data...")
                print("=" * 60)

            # Read all available lines
            while serial_connection.in_waiting > 0:
                try:
                    line = serial_connection.readline().decode('utf-8').strip()
                    if not line:
                        continue

                    # Add to log display (filters out regular posture data)
                    add_log_message(line)

                    # Print first few data lines for debugging
                    if serial_lines_printed < MAX_DEBUG_LINES:
                        if '"pitch"' in line:  # Only count posture data lines
                            serial_lines_printed += 1
                            if serial_lines_printed == MAX_DEBUG_LINES:
                                print("=" * 60)
                                print("Visualization starting...\n")

                    data = json.loads(line)

                    # Check for calibration messages
                    if 'status' in data:
                        status = data.get('status', '')
                        if status == 'calibrating':
                            current_data['calibration_status'] = 'calibrating'
                            current_data['calibration_countdown'] = data.get('countdown_s', None)
                            print(f"CALIBRATION: {data.get('countdown_s', '?')}s remaining - Hold still!")
                        elif status == 'calibrated':
                            current_data['calibration_status'] = 'calibrated'
                            current_data['calibration_countdown'] = None
                            current_data['calibration_complete_time'] = time.time()  # Record completion time
                            print(f"CALIBRATION COMPLETE! Offsets: pitch={data.get('pitch_offset', 0):.2f}°, roll={data.get('roll_offset', 0):.2f}°")
                        continue

                    # Only update if this is actual posture data
                    if 'pitch' in data and 'roll' in data:
                        # Clear calibration status once we start getting data
                        if current_data['calibration_status'] == 'calibrated':
                            current_data['calibration_status'] = None
                        # Apply exponential moving average smoothing
                        if not smoothing_initialized:
                            # First reading: initialize smoothed values
                            smoothed_pitch = data['pitch']
                            smoothed_roll = data['roll']
                            smoothing_initialized = True
                        else:
                            # Apply EMA: smoothed = α × new + (1-α) × old
                            smoothed_pitch = SMOOTHING_ALPHA * data['pitch'] + (1 - SMOOTHING_ALPHA) * smoothed_pitch
                            smoothed_roll = SMOOTHING_ALPHA * data['roll'] + (1 - SMOOTHING_ALPHA) * smoothed_roll

                        # Update current_data with smoothed values
                        data['pitch'] = smoothed_pitch
                        data['roll'] = smoothed_roll
                        current_data.update(data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

        except Exception as e:
            print(f"Error reading serial: {e}")

    else:
        # Read from log file (tail -f behavior)
        try:
            # Open file on first call
            if log_file_handle is None:
                log_file_handle = open(SERIAL_LOG, 'r')
                # Seek to end of file
                log_file_handle.seek(0, 2)
                log_file_position = log_file_handle.tell()

            # Read new lines that have been appended
            log_file_handle.seek(log_file_position)
            new_lines = log_file_handle.readlines()

            if new_lines:
                # Update position
                log_file_position = log_file_handle.tell()

                # Parse the last valid JSON line
                for line in reversed(new_lines):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # Only update if this is actual posture data
                        if 'pitch' in data and 'roll' in data:
                            # Apply exponential moving average smoothing
                            if not smoothing_initialized:
                                # First reading: initialize smoothed values
                                smoothed_pitch = data['pitch']
                                smoothed_roll = data['roll']
                                smoothing_initialized = True
                            else:
                                # Apply EMA: smoothed = α × new + (1-α) × old
                                smoothed_pitch = SMOOTHING_ALPHA * data['pitch'] + (1 - SMOOTHING_ALPHA) * smoothed_pitch
                                smoothed_roll = SMOOTHING_ALPHA * data['roll'] + (1 - SMOOTHING_ALPHA) * smoothed_roll

                            # Update current_data with smoothed values
                            data['pitch'] = smoothed_pitch
                            data['roll'] = smoothed_roll
                            current_data.update(data)
                            break
                    except json.JSONDecodeError:
                        continue

        except FileNotFoundError:
            print(f"Error: {SERIAL_LOG} not found")
        except Exception as e:
            print(f"Error reading log: {e}")

def init_plot():
    """Initialize the plot"""
    global available_ports, port_selector_text

    fig = plt.figure(figsize=(16, 9))

    # Use GridSpec for custom layout: 3D view on left, right side has 2D view, log panel, port selector (top to bottom)
    from matplotlib.gridspec import GridSpec
    gs = GridSpec(3, 2, figure=fig, width_ratios=[1, 1], height_ratios=[1.5, 1.2, 0.3], hspace=0.4)

    # Get available ports
    available_ports = get_available_ports()

    # 3D orientation view (left side, spans all 3 rows)
    ax3d = fig.add_subplot(gs[:, 0], projection='3d')
    ax3d.set_xlim([-2, 2])
    ax3d.set_ylim([-2, 2])
    ax3d.set_zlim([-2, 2])
    ax3d.set_xlabel('X (Roll axis)')
    ax3d.set_ylabel('Y (Pitch axis)')
    ax3d.set_zlabel('Z (Up)')
    ax3d.set_title('Head Orientation (Hat-Mounted MPU9250)', fontsize=14, fontweight='bold')

    # Draw reference frame
    ax3d.quiver(0, 0, 0, 2, 0, 0, color='red', arrow_length_ratio=0.1, linewidth=2, label='X (Roll)')
    ax3d.quiver(0, 0, 0, 0, 2, 0, color='green', arrow_length_ratio=0.1, linewidth=2, label='Y (Pitch)')
    ax3d.quiver(0, 0, 0, 0, 0, 2, color='blue', arrow_length_ratio=0.1, linewidth=2, label='Z (Up)')

    # 2D angle indicators (top right - row 0)
    ax2d = fig.add_subplot(gs[0, 1])
    ax2d.set_xlim([-90, 90])   # Roll: ±90° for full left/right range
    ax2d.set_ylim([-90, 90])   # Pitch: ±90° for full forward/backward range
    ax2d.set_xlabel('Roll (degrees)', fontsize=12)
    ax2d.set_ylabel('Pitch (degrees)', fontsize=12)
    ax2d.set_title('Angle Indicators', fontsize=14, fontweight='bold')
    ax2d.grid(True, alpha=0.3)
    ax2d.axhline(0, color='black', linewidth=0.5)
    ax2d.axvline(0, color='black', linewidth=0.5)

    # Draw threshold zones - all four quadrants
    threshold = 15.0
    # Top zone: Pitch forward (looking down)
    slouch_zone_top = Rectangle((-90, threshold), 180, 90-threshold,
                           alpha=0.25, color='#FF4444', label='Slouch Zones')
    ax2d.add_patch(slouch_zone_top)

    # Bottom zone: Pitch backward (looking up)
    slouch_zone_bottom = Rectangle((-90, -90), 180, 90-threshold,
                           alpha=0.25, color='#FF4444')
    ax2d.add_patch(slouch_zone_bottom)

    # Left zone: Roll left (head to left shoulder)
    slouch_zone_left = Rectangle((-90, -threshold), 90-threshold, 2*threshold,
                           alpha=0.25, color='#FF8800')
    ax2d.add_patch(slouch_zone_left)

    # Right zone: Roll right (head to right shoulder)
    slouch_zone_right = Rectangle((threshold, -threshold), 90-threshold, 2*threshold,
                           alpha=0.25, color='#FF8800')
    ax2d.add_patch(slouch_zone_right)

    # Center good posture zone
    good_zone = Rectangle((-threshold, -threshold), 2*threshold, 2*threshold,
                         alpha=0.35, color='#44FF44', label='Good Posture')
    ax2d.add_patch(good_zone)

    # Threshold lines
    ax2d.axhline(threshold, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax2d.axhline(-threshold, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax2d.axvline(threshold, color='orange', linestyle='--', linewidth=2, alpha=0.7)
    ax2d.axvline(-threshold, color='orange', linestyle='--', linewidth=2, alpha=0.7)

    ax2d.legend(loc='upper right')

    # Log panel (middle right - row 1)
    ax_log = fig.add_subplot(gs[1, 1])
    ax_log.set_xlim([0, 1])
    ax_log.set_ylim([0, 1])
    ax_log.axis('off')
    ax_log.set_title('Arduino Status Log', fontsize=12, fontweight='bold', loc='left')

    # Port selector panel (bottom right - row 2)
    ax_port = fig.add_subplot(gs[2, 1])
    ax_port.set_xlim([0, 1])
    ax_port.set_ylim([0, 1])
    ax_port.axis('off')
    ax_port.set_title('Serial Port Selector', fontsize=11, fontweight='bold', loc='left')

    # Create port selection buttons
    port_buttons = []
    if available_ports:
        # Create a button for each port
        for i, (port_device, port_desc) in enumerate(available_ports[:3]):  # Show max 3 ports
            btn_ax = plt.axes([0.52 + i * 0.15, 0.02, 0.13, 0.04])
            btn = Button(btn_ax, port_device.split('/')[-1], color='lightblue', hovercolor='lightgreen')

            # Button callback
            def make_callback(port):
                def callback(event):
                    switch_serial_port(port)
                return callback

            btn.on_clicked(make_callback(port_device))
            port_buttons.append(btn)
    else:
        ax_port.text(0.5, 0.5, 'No serial ports detected',
                    ha='center', va='center', fontsize=10, color='red', style='italic')

    return fig, ax3d, ax2d, ax_log, ax_port, port_buttons

def update_plot(frame, fig, ax3d, ax2d, ax_port, ax_log):
    """Update the plot with new data"""
    read_latest_data()

    pitch = current_data['pitch']
    roll = current_data['roll']
    pitch_raw = current_data['pitch_raw']
    slouch = current_data['forward_slouch']
    alert_level = current_data['alert_level_name']
    cumulative = current_data['cumulative_slouch_s']
    threshold = current_data['threshold']

    # Clear previous frame
    ax3d.clear()
    ax2d.clear()
    ax_port.clear()
    ax_log.clear()

    # Redraw 3D view
    ax3d.set_xlim([-2, 2])
    ax3d.set_ylim([-2, 2])
    ax3d.set_zlim([-2, 2])
    ax3d.set_xlabel('X (Roll axis)')
    ax3d.set_ylabel('Y (Pitch axis)')
    ax3d.set_zlabel('Z (Up)')

    # Draw reference frame
    ax3d.quiver(0, 0, 0, 1.5, 0, 0, color='red', arrow_length_ratio=0.15, linewidth=1.5, alpha=0.5)
    ax3d.quiver(0, 0, 0, 0, 1.5, 0, color='green', arrow_length_ratio=0.15, linewidth=1.5, alpha=0.5)
    ax3d.quiver(0, 0, 0, 0, 0, 1.5, color='blue', arrow_length_ratio=0.15, linewidth=1.5, alpha=0.5)

    # Create and rotate cube
    cube_faces = create_cube()
    rotated_faces = rotate_cube(cube_faces, pitch, roll)

    # Color faces based on posture status
    face_colors = ['cyan', 'cyan', 'yellow', 'yellow', 'lightblue', 'gray']
    if slouch:
        face_colors = ['red', 'red', 'orange', 'orange', 'pink', 'darkred']

    # Draw cube
    cube = Poly3DCollection(rotated_faces, facecolors=face_colors,
                           linewidths=2, edgecolors='black', alpha=0.8)
    ax3d.add_collection3d(cube)

    # Add orientation vector (pointing forward from sensor)
    forward_vector = rotation_matrix_y(pitch) @ rotation_matrix_x(roll) @ np.array([0, 1.5, 0])
    ax3d.quiver(0, 0, 0, forward_vector[0], forward_vector[1], forward_vector[2],
               color='purple', arrow_length_ratio=0.2, linewidth=3, label='Forward')

    # Title with status
    status_color = get_alert_color(alert_level)
    status_text = f"{'SLOUCHING' if slouch else 'GOOD POSTURE'} | Alert: {alert_level.upper()}"
    ax3d.set_title(status_text, fontsize=14, fontweight='bold', color=status_color)

    # Redraw 2D angle view
    ax2d.set_xlim([-90, 90])   # Roll: ±90° for full left/right range
    ax2d.set_ylim([-90, 90])   # Pitch: ±90° for full forward/backward range
    ax2d.set_xlabel('Roll (degrees)', fontsize=12)
    ax2d.set_ylabel('Pitch (degrees)', fontsize=12)
    ax2d.set_title(f'Pitch: {pitch:.1f}° | Roll: {roll:.1f}°',
                  fontsize=14, fontweight='bold')
    ax2d.grid(True, alpha=0.3)
    ax2d.axhline(0, color='black', linewidth=0.5)
    ax2d.axvline(0, color='black', linewidth=0.5)

    # Draw threshold zones - all four quadrants
    # Top zone: Pitch forward (looking down)
    slouch_zone_top = Rectangle((-90, threshold), 180, 90-threshold,
                           alpha=0.25, color='#FF4444', label='Slouch Zones')
    ax2d.add_patch(slouch_zone_top)

    # Bottom zone: Pitch backward (looking up)
    slouch_zone_bottom = Rectangle((-90, -90), 180, 90-threshold,
                           alpha=0.25, color='#FF4444')
    ax2d.add_patch(slouch_zone_bottom)

    # Left zone: Roll left (head to left shoulder)
    slouch_zone_left = Rectangle((-90, -threshold), 90-threshold, 2*threshold,
                           alpha=0.25, color='#FF8800')
    ax2d.add_patch(slouch_zone_left)

    # Right zone: Roll right (head to right shoulder)
    slouch_zone_right = Rectangle((threshold, -threshold), 90-threshold, 2*threshold,
                           alpha=0.25, color='#FF8800')
    ax2d.add_patch(slouch_zone_right)

    # Center good posture zone
    good_zone = Rectangle((-threshold, -threshold), 2*threshold, 2*threshold,
                         alpha=0.35, color='#44FF44', label='Good Posture')
    ax2d.add_patch(good_zone)

    # Draw threshold lines
    ax2d.axhline(threshold, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Pitch ±15°')
    ax2d.axhline(-threshold, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax2d.axvline(threshold, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Roll ±15°')
    ax2d.axvline(-threshold, color='orange', linestyle='--', linewidth=2, alpha=0.7)

    # Plot current position
    marker_color = 'red' if slouch else 'green'
    marker_size = 200 if slouch else 150
    ax2d.scatter(roll, pitch, s=marker_size, c=marker_color,
                marker='o', edgecolors='black', linewidth=2, zorder=10)

    # Add text annotations
    ax2d.text(0.02, 0.98, f'Raw Pitch: {pitch_raw:.1f}°',
             transform=ax2d.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax2d.text(0.02, 0.90, f'Cumulative: {cumulative}s',
             transform=ax2d.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # Show calibration status overlay
    calibration_status = current_data.get('calibration_status')
    if calibration_status == 'calibrating':
        countdown = current_data.get('calibration_countdown', '?')
        # Large centered overlay on both plots
        fig.text(0.5, 0.5, f'CALIBRATING\n{countdown}s\nHOLD STILL!',
                ha='center', va='center', fontsize=32, fontweight='bold',
                color='white',
                bbox=dict(boxstyle='round,pad=1', facecolor='orange', alpha=0.9, edgecolor='red', linewidth=4))
    elif calibration_status == 'calibrated':
        # Auto-clear after 2 seconds
        complete_time = current_data.get('calibration_complete_time')
        if complete_time and (time.time() - complete_time < 2.0):
            # Brief "complete" message (shows for 2 seconds)
            fig.text(0.5, 0.5, 'CALIBRATION\nCOMPLETE!',
                    ha='center', va='center', fontsize=28, fontweight='bold',
                    color='white',
                    bbox=dict(boxstyle='round,pad=1', facecolor='green', alpha=0.9, edgecolor='darkgreen', linewidth=4))
        else:
            # Clear status after 2 seconds
            current_data['calibration_status'] = None

    ax2d.legend(loc='upper right')

    # Render port selector panel
    ax_port.set_xlim([0, 1])
    ax_port.set_ylim([0, 1])
    ax_port.axis('off')

    # Display current port (above the buttons area)
    current_port_display = current_serial_port if current_serial_port else SERIAL_PORT
    conn_status = "Connected" if serial_connection and serial_connection.is_open else "Disconnected"
    conn_color = 'green' if serial_connection and serial_connection.is_open else 'red'

    # Shortened port name for display
    port_short = current_port_display.split('/')[-1] if current_port_display else "None"

    ax_port.text(0.01, 0.85, f'Port: {port_short}',
                fontsize=9, fontweight='bold', verticalalignment='top')
    ax_port.text(0.35, 0.85, f'| Status: {conn_status}',
                fontsize=9, verticalalignment='top', color=conn_color, fontweight='bold')

    # Render log panel
    ax_log.set_xlim([0, 1])
    ax_log.set_ylim([0, 1])
    ax_log.axis('off')
    ax_log.set_title('Arduino Status Log', fontsize=11, fontweight='bold', loc='left')

    # Display recent log messages (newest at bottom)
    if log_messages:
        y_position = 0.95
        y_step = 0.95 / MAX_LOG_MESSAGES

        for msg in log_messages:
            # Color code by message type
            if 'ERROR' in msg:
                color = 'red'
                weight = 'bold'
            elif 'DEBUG' in msg:
                color = 'blue'
                weight = 'normal'
            elif 'STATUS' in msg:
                color = 'green'
                weight = 'normal'
            else:
                color = 'black'
                weight = 'normal'

            ax_log.text(0.02, y_position, msg, fontsize=8,
                       verticalalignment='top', fontfamily='monospace',
                       color=color, fontweight=weight)
            y_position -= y_step
    else:
        # No messages yet
        ax_log.text(0.5, 0.5, 'Waiting for Arduino messages...',
                   ha='center', va='center', fontsize=10, color='gray', style='italic')

    return ax3d, ax2d, ax_port, ax_log

def main():
    """Main visualization loop"""
    print("=" * 60)
    print("  Posture Monitor - 3D Orientation Visualizer")
    print("=" * 60)
    if USE_SERIAL_PORT:
        print(f"Reading from serial port: {SERIAL_PORT}")
        print(f"Baud rate: {BAUD_RATE}")
    else:
        print(f"Reading from log file: {SERIAL_LOG}")
    print("Press Ctrl+C to stop")
    print()

    try:
        # Initialize plot
        fig, ax3d, ax2d, ax_log, ax_port, port_buttons = init_plot()

        # Create animation
        anim = FuncAnimation(fig, update_plot, fargs=(fig, ax3d, ax2d, ax_port, ax_log),
                           interval=UPDATE_INTERVAL, blit=False, cache_frame_data=False)

        # Note: tight_layout() is incompatible with Button widgets, but we use GridSpec with explicit spacing
        plt.show()

    except KeyboardInterrupt:
        print("\n\nVisualization stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
