# THực hiện cấu hình phần cứng và phần mềm để đọc GPS.
## 1. Cấu hình phần cứng
### Sơ đồ kết nối chân UART 
| GPS NEO 7M | Raspberrypi 4B |
|-------|-------|
| VCC | 3.3V |
| GND | GND |
| TX  | GPIO15 (RXD0/ Pin số 10) |

### **Lưu ý**: Khi LED PPS trên module nhấp nháy 1Hz, nghĩa là GPS fix vị trí thành công.

## 2. Cấu hình phần mềm
### Cài thư viện cần thiết
```c
sudo apt update
sudo apt install python3-pip python3-serial -y
pip3 install pynmea2 geopy folium
```

### Cấu hình UART trên Raspberry Pi
#### 1. Mở cấu hình
```c
sudo raspi-config
```
#### 2. Vào menu
`Interface Options` -> `Serial Port`
-   Chọn **NO** khi hỏi “Would you like a login shell to be accessible over serial?”.
-   Chọn **YES** khi hỏi “Would you like the serial port hardware to be enabled?”

#### 3. Khởi động lại:
```c
sudo reboot
```
#### 4. Kiểm tra lại cổng
```c
ls -l /dev/serial*
```
- Nếu thấy `/dev/serial0 -> ttyS0` thì bạn có thể sử dụng `/dev/ttyS0`.
### Chạy chương trình
```c
python3 gps_map.py
```
### Chú ý:
Nếu GPS không phản hồi , thử tắt dịch vụ gpsd:
```c
sudo systemctl stop gpsd.socket
sudo systemctl disable gpsd.socket
```