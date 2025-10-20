import serial
import csv
from datetime import datetime
import folium
import threading
import time
from pyubx2 import UBXReader
import os

SERIAL_PORT = "COM7"
BAUDRATE = 115200
CSV_FILE = os.path.join("e:/GPS/GPS_v2", "gps_log.csv")
MAP_FILE = os.path.join("e:/GPS/GPS_v2", "gps_map.html")
UPDATE_INTERVAL = 5

gps_points = []

def log_gps(lat, lon, height=0, speed=0, numSV=0):
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(['timestamp', 'latitude', 'longitude', 'height_m', 'speed_m_s', 'numSV'])
        writer.writerow([datetime.now(), lat, lon, height, speed, numSV])
    gps_points.append((lat, lon))
    print(f"[LOG] {datetime.now()} | Lat: {lat:.7f} Lon: {lon:.7f} H: {height:.2f} Speed: {speed:.2f} SV: {numSV}")

def update_map():
    while True:
        if gps_points:
            map_center = gps_points[0]
            m = folium.Map(location=map_center, zoom_start=18)
            for lat, lon in gps_points:
                folium.CircleMarker([lat, lon], radius=4, color='red').add_to(m)
            folium.PolyLine(gps_points, color="blue", weight=2.5, opacity=0.8).add_to(m)
            m.save(MAP_FILE)
            print(f"[MAP] Map updated: {MAP_FILE}")
        time.sleep(UPDATE_INTERVAL)

def read_gps():
    with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1) as port:
        ubr = UBXReader(port)
        for _, parsed in ubr:
            if parsed.identity == "NAV-PVT" and parsed.fixType >= 3 and parsed.gnssFixOk == 1:
                lat = parsed.lat       # sử dụng trực tiếp
                lon = parsed.lon
                height = parsed.height / 1000
                speed = parsed.gSpeed / 1000
                numSV = parsed.numSV
                log_gps(lat, lon, height, speed, numSV)

if __name__ == "__main__":
    threading.Thread(target=update_map, daemon=True).start()
    read_gps()
