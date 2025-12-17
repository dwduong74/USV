# Dự án USV PTIT

Kho lưu trữ này chứa không gian làm việc ROS 2 (ROS 2 workspace) cho dự án Tàu không người lái (Unmanned Surface Vehicle - USV), có thể dành cho PTIT.

## Cấu trúc kho lưu trữ

- **`src/`**: Thư mục mã nguồn của không gian làm việc ROS 2.
  - `ros2_astra_camera`: Gói cho camera 3D Astra.
  - `rosbag_recorder`: Một gói đơn giản để ghi lại các topic ROS.
  - `usv_gps`: Gói để đọc, lọc và xử lý dữ liệu GPS cho USV.
- **`Esp32_source/`**: Chứa mã nguồn cho vi điều khiển ESP32, có thể xử lý việc điều khiển cấp thấp hoặc giao tiếp cảm biến.
- **`GPS/`**: Có thể chứa dữ liệu, nhật ký hoặc các script tiện ích liên quan đến GPS.

## Yêu cầu

- ROS 2 (Giả định là bản Humble).
- Python 3
- Các phụ thuộc Python cho gói `usv_gps`.

## Cách cài đặt phụ thuộc

Gói `usv_gps` yêu cầu một số thư viện Python. Bạn có thể cài đặt chúng bằng `pip`:

```bash
pip install pyubx2 numpy folium
```
Bạn cũng có thể cần cài đặt các phụ thuộc cho các gói ROS khác. Sử dụng `rosdep` để làm việc này:
```bash
rosdep install --from-paths src --ignore-src -r -y
```

## Cách biên dịch (Build)

1.  Di chuyển đến thư mục gốc của không gian làm việc:
    ```bash
    cd USV
    ```
2.  Biên dịch không gian làm việc bằng `colcon`:
    ```bash
    colcon build
    ```

## Cách chạy

Sau khi biên dịch thành công, hãy thực thi tệp cài đặt để các gói có sẵn trong terminal của bạn:

```bash
source install/setup.bash
```

Sau đó, bạn có thể sử dụng `ros2 launch` hoặc `ros2 run` để khởi chạy các node từ các gói khác nhau.