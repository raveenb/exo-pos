#!/Users/raveenbeemsingh/Developer/exo-pos/.venv/bin/python3
"""
Real-time 3D Orientation Visualizer for Posture Monitor

Reads JSON data from serial log and displays:
- 3D cube representing sensor orientation (pitch and roll)
- Real-time angle indicators
- Posture status and alerts

Requirements:
    pip install matplotlib numpy
"""

import json
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# Configuration
import os
SERIAL_PORT = '/dev/cu.usbmodem212401'
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
    'threshold': 15.0
}

# File/Serial tracking
log_file_handle = None
log_file_position = 0
serial_connection = None

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

def read_latest_data():
    """Read data from serial port or log file"""
    global current_data, log_file_handle, log_file_position, serial_connection

    if USE_SERIAL_PORT:
        # Read directly from serial port
        try:
            import serial as pyserial

            # Open serial connection on first call
            if serial_connection is None:
                serial_connection = pyserial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
                print(f"Connected to {SERIAL_PORT} @ {BAUD_RATE} baud")

            # Read all available lines
            while serial_connection.in_waiting > 0:
                try:
                    line = serial_connection.readline().decode('utf-8').strip()
                    if not line:
                        continue

                    data = json.loads(line)
                    # Only update if this is actual posture data
                    if 'pitch' in data and 'roll' in data:
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
    fig = plt.figure(figsize=(14, 8))

    # 3D orientation view
    ax3d = fig.add_subplot(121, projection='3d')
    ax3d.set_xlim([-2, 2])
    ax3d.set_ylim([-2, 2])
    ax3d.set_zlim([-2, 2])
    ax3d.set_xlabel('X (Roll axis)')
    ax3d.set_ylabel('Y (Pitch axis)')
    ax3d.set_zlabel('Z (Up)')
    ax3d.set_title('Sensor Orientation (MPU9250)', fontsize=14, fontweight='bold')

    # Draw reference frame
    ax3d.quiver(0, 0, 0, 2, 0, 0, color='red', arrow_length_ratio=0.1, linewidth=2, label='X (Roll)')
    ax3d.quiver(0, 0, 0, 0, 2, 0, color='green', arrow_length_ratio=0.1, linewidth=2, label='Y (Pitch)')
    ax3d.quiver(0, 0, 0, 0, 0, 2, color='blue', arrow_length_ratio=0.1, linewidth=2, label='Z (Up)')

    # 2D angle indicators
    ax2d = fig.add_subplot(122)
    ax2d.set_xlim([-30, 30])
    ax2d.set_ylim([-30, 30])
    ax2d.set_xlabel('Roll (degrees)', fontsize=12)
    ax2d.set_ylabel('Pitch (degrees)', fontsize=12)
    ax2d.set_title('Angle Indicators', fontsize=14, fontweight='bold')
    ax2d.grid(True, alpha=0.3)
    ax2d.axhline(0, color='black', linewidth=0.5)
    ax2d.axvline(0, color='black', linewidth=0.5)

    # Draw threshold zones
    threshold = 15.0
    slouch_zone = Rectangle((-30, threshold), 60, 30-threshold,
                           alpha=0.2, color='red', label='Slouch Zone')
    ax2d.add_patch(slouch_zone)

    good_zone = Rectangle((-30, -threshold), 60, 2*threshold,
                         alpha=0.2, color='green', label='Good Posture')
    ax2d.add_patch(good_zone)

    ax2d.legend(loc='upper right')

    return fig, ax3d, ax2d

def update_plot(frame, fig, ax3d, ax2d):
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
    ax2d.set_xlim([-30, 30])
    ax2d.set_ylim([-30, 30])
    ax2d.set_xlabel('Roll (degrees)', fontsize=12)
    ax2d.set_ylabel('Pitch (degrees)', fontsize=12)
    ax2d.set_title(f'Pitch: {pitch:.1f}° | Roll: {roll:.1f}°',
                  fontsize=14, fontweight='bold')
    ax2d.grid(True, alpha=0.3)
    ax2d.axhline(0, color='black', linewidth=0.5)
    ax2d.axvline(0, color='black', linewidth=0.5)

    # Draw threshold zones
    slouch_zone = Rectangle((-30, threshold), 60, 30-threshold,
                           alpha=0.2, color='red', label='Slouch Zone')
    ax2d.add_patch(slouch_zone)

    good_zone = Rectangle((-30, -threshold), 60, 2*threshold,
                         alpha=0.2, color='green', label='Good Posture')
    ax2d.add_patch(good_zone)

    # Draw threshold lines
    ax2d.axhline(threshold, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax2d.axhline(-threshold, color='blue', linestyle='--', linewidth=2, alpha=0.7)

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

    ax2d.legend(loc='upper right')

    return ax3d, ax2d

def main():
    """Main visualization loop"""
    print("=" * 60)
    print("  Posture Monitor - 3D Orientation Visualizer")
    print("=" * 60)
    print(f"Reading from: {SERIAL_LOG}")
    print("Press Ctrl+C to stop")
    print()

    try:
        # Initialize plot
        fig, ax3d, ax2d = init_plot()

        # Create animation
        anim = FuncAnimation(fig, update_plot, fargs=(fig, ax3d, ax2d),
                           interval=UPDATE_INTERVAL, blit=False, cache_frame_data=False)

        plt.tight_layout()
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
