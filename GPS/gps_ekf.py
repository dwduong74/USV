#!/usr/bin/env python3
"""
gps_ekf_logger.py
- Read NMEA from serial (/dev/serial0)
- Buffer many raw samples (BUFFER_SIZE)
- Average raw samples each cycle -> measurement (lat, lon)
- Use FilterPy KalmanFilter on state [lat, lon, v_lat, v_lon] (units: degrees, degrees/s)
- Output filtered lat/lon at TARGET_HZ, log CSV, update folium map periodically, auto-open browser
"""

import serial
import pynmea2
import time
import csv
import webbrowser
import os
from datetime import datetime
import numpy as np
from filterpy.kalman import KalmanFilter
import folium

# ---------------- CONFIG ----------------
SERIAL_PORT = "/dev/ttyS0"   # adjust if necessary
BAUDRATE = 115200              # your device's baudrate
BUFFER_SIZE = 250              # keep up to N recent raw samples (200-300 as you wanted)
MIN_SAMPLES_FOR_UPDATE = 10    # minimum samples before starting filter
TARGET_HZ = 15.0               # desired output frequency (Hz)
CSV_FILE = "log.csv"
MAP_FILE = "gps_map.html"
MAP_UPDATE_INTERVAL = 10.0     # seconds between folium map saves (real-time updates)
AUTO_OPEN_MAP = True           # auto open map in browser on first save

# Kalman tuning (units: degrees)
# GPS accuracy ~5 m -> degrees ≈ 5 / 111320 ≈ 4.49e-5
MEASUREMENT_STD_DEG = 5e-5     # sigma of measurement noise in degrees (tune as needed)
MEASUREMENT_VAR = MEASUREMENT_STD_DEG ** 2

# Process noise: how much we allow state to change per dt
PROCESS_POS_STD_DEG = 1e-5    # position process std (deg)
PROCESS_VEL_STD_DEG = 1e-5    # velocity process std (deg/s)
# ----------------------------------------

# Serial init
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)

# Buffers
lat_buf = []
lon_buf = []
time_buf = []

# Path points (filtered lat/lon)
path_points = []

# CSV header
with open(CSV_FILE, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["timestamp", "avg_raw_lat", "avg_raw_lon", "filtered_lat", "filtered_lon", "v_lat_deg_s", "v_lon_deg_s"])

# Kalman filter: state [lat, lon, v_lat, v_lon], measurement [lat, lon]
kf = KalmanFilter(dim_x=4, dim_z=2)
# initialize F (will be set each cycle according to dt)
kf.F = np.eye(4)
kf.H = np.array([[1., 0., 0., 0.],
                 [0., 1., 0., 0.]])
kf.x = np.zeros((4, 1))   # initial state
kf.P = np.eye(4) * 1e3    # large initial uncertainty
kf.R = np.array([[MEASUREMENT_VAR, 0.],
                 [0., MEASUREMENT_VAR]])
# Q set per dt in function below

def set_F_Q(dt):
    """Set transition matrix F and process noise Q depending on dt (units: seconds)."""
    F = np.array([[1., 0., dt, 0.],
                  [0., 1., 0., dt],
                  [0., 0., 1., 0.],
                  [0., 0., 0., 1.]])
    # simple diagonal Q: position and velocity process noise (deg and deg/s)
    q_pos = (PROCESS_POS_STD_DEG ** 2) * dt
    q_vel = (PROCESS_VEL_STD_DEG ** 2) * dt
    Q = np.diag([q_pos, q_pos, q_vel, q_vel])
    kf.F = F
    kf.Q = Q

# Control variables
first_map_opened = False
last_map_update = 0.0
last_output_time = time.time()

print("GPS EKF logger starting. Serial:", SERIAL_PORT, "baud", BAUDRATE)
print("Buffer size:", BUFFER_SIZE, "Target Hz:", TARGET_HZ)

try:
    while True:
        cycle_start = time.time()
        # Read available NMEA lines quickly (non-blocking style)
        while ser.in_waiting:
            raw = ser.readline().decode('ascii', errors='replace').strip()
            if not raw:
                continue
            # Accept typical position sentences
            if raw.startswith(('$GPRMC', '$GNRMC', '$GPGGA', '$GNGGA')):
                try:
                    msg = pynmea2.parse(raw)
                except pynmea2.ParseError:
                    continue
                if not hasattr(msg, 'latitude') or not hasattr(msg, 'longitude'):
                    continue
                lat = msg.latitude
                lon = msg.longitude
                # sometimes 0.0, skip those
                if lat == 0.0 and lon == 0.0:
                    continue
                lat_buf.append(lat)
                lon_buf.append(lon)
                time_buf.append(time.time())
                if len(lat_buf) > BUFFER_SIZE:
                    lat_buf.pop(0)
                    lon_buf.pop(0)
                    time_buf.pop(0)

        # If enough samples, compute average raw measurement
        if len(lat_buf) >= MIN_SAMPLES_FOR_UPDATE:
            avg_lat = sum(lat_buf) / len(lat_buf)
            avg_lon = sum(lon_buf) / len(lon_buf)
            avg_time = sum(time_buf) / len(time_buf)

            # Initialize map center and kf.x on first valid measurement
            if not path_points:
                # set initial state lat/lon and zero velocity
                kf.x = np.array([[avg_lat], [avg_lon], [0.0], [0.0]])
                print("Reference/initial position set:", f"{avg_lat:.6f}, {avg_lon:.6f}")

            # KF predict/update with dt = 1/TARGET_HZ
            dt = 1.0 / TARGET_HZ
            set_F_Q(dt)
            kf.predict()
            kf.update(np.array([avg_lat, avg_lon]))

            # Extract filtered state
            filt_lat = float(kf.x[0, 0])
            filt_lon = float(kf.x[1, 0])
            v_lat = float(kf.x[2, 0])
            v_lon = float(kf.x[3, 0])

            # Append to path and CSV
            path_points.append((filt_lat, filt_lon))
            with open(CSV_FILE, "a", newline="") as f:
                w = csv.writer(f)
                w.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    f"{avg_lat:.6f}", f"{avg_lon:.6f}",
                    f"{filt_lat:.6f}", f"{filt_lon:.6f}",
                    f"{v_lat:.8f}", f"{v_lon:.8f}"
                ])

            # Print filtered output at TARGET_HZ
            now = time.time()
            if now - last_output_time >= (1.0 / TARGET_HZ) - 1e-6:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Filtered Lat: {filt_lat:.6f}, Lon: {filt_lon:.6f} | v_lat: {v_lat:.8f} deg/s, v_lon: {v_lon:.8f} deg/s")
                last_output_time = now

            # Periodic map update
            if time.time() - last_map_update >= MAP_UPDATE_INTERVAL:
                # Create folium map centered on first point (or current filtered)
                center = path_points[0] if path_points else (filt_lat, filt_lon)
                m = folium.Map(location=[center[0], center[1]], zoom_start=17)
                # marker for current filtered position
                folium.Marker([filt_lat, filt_lon], tooltip="Filtered position").add_to(m)
                # polyline for path
                if len(path_points) > 1:
                    folium.PolyLine(path_points, weight=3).add_to(m)
                m.save(MAP_FILE)
                # Auto-open browser on first creation
                if AUTO_OPEN_MAP and not first_map_opened:
                    try:
                        webbrowser.open('file://' + os.path.realpath(MAP_FILE))
                        first_map_opened = True
                    except Exception as e:
                        print("Could not auto-open browser:", e)
                print(f"Map updated: {MAP_FILE} (points: {len(path_points)})")
                last_map_update = time.time()

        # Sleep to maintain target Hz
        elapsed = time.time() - cycle_start
        target_period = 1.0 / TARGET_HZ
        if elapsed < target_period:
            time.sleep(target_period - elapsed)

except KeyboardInterrupt:
    print("Program stopped by user.")
except serial.SerialException as e:
    print("Serial error:", e)
finally:
    try:
        if ser and ser.is_open:
            ser.close()
    except Exception:
        pass
