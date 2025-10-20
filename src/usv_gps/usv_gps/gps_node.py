#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
import serial
import csv
from datetime import datetime
import folium
import threading
import time
from pyubx2 import UBXReader
import os

# Configuration
SERIAL_PORT = "/dev/ttyS0"  # For Raspberry Pi, as per README
BAUDRATE = 115200
CSV_FILE = os.path.expanduser("~/USV/GPS/gps_log.csv")
MAP_FILE = os.path.expanduser("~/USV/GPS/gps_map.html")
UPDATE_INTERVAL = 5

class GpsNode(Node):
    def __init__(self):
        super().__init__('gps_node')
        self.publisher_ = self.create_publisher(NavSatFix, 'gps/fix', 10)
        self.get_logger().info('GPS Node has been started.')

        self.gps_points = []

        # Start the map update thread
        self.map_thread = threading.Thread(target=self.update_map, daemon=True)
        self.map_thread.start()

        # Start the GPS reading loop
        self.read_thread = threading.Thread(target=self.read_gps, daemon=True)
        self.read_thread.start()

    def log_and_publish_gps(self, lat, lon, height=0, speed=0, numSV=0):
        # Log to CSV
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
        with open(CSV_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['timestamp', 'latitude', 'longitude', 'height_m', 'speed_m_s', 'numSV'])
            writer.writerow([datetime.now(), lat, lon, height, speed, numSV])
        
        self.gps_points.append((lat, lon))
        self.get_logger().info(f"[LOG] {datetime.now()} | Lat: {lat:.7f} Lon: {lon:.7f} H: {height:.2f} Speed: {speed:.2f} SV: {numSV}")

        # Publish NavSatFix message
        msg = NavSatFix()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'gps_link'
        msg.latitude = lat
        msg.longitude = lon
        msg.altitude = height
        msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publishing: Lat={lat:.6f}, Lon={lon:.6f}')

    def update_map(self):
        while rclpy.ok():
            if self.gps_points:
                points_to_map = list(self.gps_points)
                if points_to_map:
                    map_center = points_to_map[-1]
                    m = folium.Map(location=map_center, zoom_start=18)
                    for lat, lon in points_to_map:
                        folium.CircleMarker([lat, lon], radius=4, color='red').add_to(m)
                    if len(points_to_map) > 1:
                        folium.PolyLine(points_to_map, color="blue", weight=2.5, opacity=0.8).add_to(m)
                    os.makedirs(os.path.dirname(MAP_FILE), exist_ok=True)
                    m.save(MAP_FILE)
                    self.get_logger().info(f"[MAP] Map updated: {MAP_FILE}")
            time.sleep(UPDATE_INTERVAL)

    def read_gps(self):
        while rclpy.ok():
            try:
                with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1) as port:
                    self.get_logger().info(f"Successfully opened serial port {SERIAL_PORT}")
                    ubr = UBXReader(port)
                    for _, parsed in ubr:
                        if not rclpy.ok():
                            break
                        if parsed.identity == "NAV-PVT" and parsed.fixType >= 3 and parsed.gnssFixOk == 1:
                            lat = parsed.lat
                            lon = parsed.lon
                            height = parsed.height / 1000.0
                            speed = parsed.gSpeed / 1000.0
                            numSV = parsed.numSV
                            self.log_and_publish_gps(lat, lon, height, speed, numSV)
            except serial.SerialException as e:
                self.get_logger().error(f"Serial port error: {e}. Retrying in 5 seconds.")
                time.sleep(5)
            except Exception as e:
                self.get_logger().error(f"An unexpected error occurred: {e}. Retrying in 5 seconds.")
                time.sleep(5)


def main(args=None):
    rclpy.init(args=args)
    node = GpsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
