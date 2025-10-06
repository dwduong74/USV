#!/usr/bin/env python3
"""
Rosbag recorder node (ROS2, rclpy).
Features:
 - dịch vụ /rosbag_recorder/start  (std_srvs/Trigger)
 - dịch vụ /rosbag_recorder/stop   (std_srvs/Trigger)
 - dịch vụ /rosbag_recorder/status (std_srvs/Trigger) -> báo đang ghi hay không
 - topic /rosbag_recorder/cmd (std_msgs/String) nhận "start", "stop", "restart"
 - parameters để cấu hình topics, output_dir, bag_prefix, additional_args, auto_start
Run:
  source /opt/ros/<distro>/setup.bash
  python3 rosbag_recorder.py
Or install into package and launch normally.
"""
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from std_msgs.msg import String
import subprocess
import shlex
import os
import signal
import threading
from datetime import datetime
import time

def _timestamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')

class RosbagRecorder(Node):
    def __init__(self):
        super().__init__('rosbag_recorder')

        # PARAMETERS (có thể override khi launch)
        self.declare_parameter('topics', [])            # list of topic strings
        self.declare_parameter('record_all', False)     # bool
        self.declare_parameter('output_dir', os.path.join(os.getcwd(), 'rosbags'))
        self.declare_parameter('bag_prefix', 'bag')
        self.declare_parameter('additional_args', '')   # extra args string to append to ros2 bag
        self.declare_parameter('auto_start', False)     # auto start on node init
        self.declare_parameter('start_delay', 0.0)      # seconds delay before auto-start

        self._process = None
        self._lock = threading.Lock()
        self._stdout_thread = None
        self._stderr_thread = None

        # SERVICES
        self.srv_start = self.create_service(Trigger, 'rosbag_recorder/start', self._srv_start_cb)
        self.srv_stop  = self.create_service(Trigger, 'rosbag_recorder/stop',  self._srv_stop_cb)
        self.srv_status= self.create_service(Trigger, 'rosbag_recorder/status', self._srv_status_cb)

        # CMD topic (text commands)
        self.cmd_sub = self.create_subscription(String, 'rosbag_recorder/cmd', self._cmd_cb, 10)

        self.get_logger().info('rosbag_recorder ready. Services: /rosbag_recorder/{start,stop,status}. Topic: rosbag_recorder/cmd')

        # auto-start if requested
        if self.get_parameter('auto_start').value:
            delay = float(self.get_parameter('start_delay').value or 0.0)
            self.get_logger().info(f'Auto-start enabled: starting in {delay} seconds...')
            threading.Timer(delay, self._auto_start).start()

    # ---------- helper to stream subprocess output to rclpy logger ----------
    def _stream_reader(self, pipe, log_fn):
        try:
            with pipe:
                for raw in iter(pipe.readline, b''):
                    if not raw:
                        break
                    try:
                        s = raw.decode(errors='ignore').rstrip()
                    except Exception:
                        s = str(raw)
                    log_fn(s)
        except Exception as e:
            self.get_logger().error(f'stream_reader exception: {e}')

    # ---------- build ros2 bag record command ----------
    def _build_cmd(self):
        topics = self.get_parameter('topics').value or []
        record_all = bool(self.get_parameter('record_all').value)
        output_dir = str(self.get_parameter('output_dir').value)
        bag_prefix = str(self.get_parameter('bag_prefix').value)
        additional_args = str(self.get_parameter('additional_args').value or '')

        # ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # create unique prefix with timestamp
        out_name = f"{bag_prefix}_{_timestamp()}"
        out_path = os.path.join(output_dir, out_name)

        cmd = ['ros2', 'bag', 'record', '-o', out_path]

        if record_all:
            cmd.append('-a')
        else:
            if not topics:
                # no topics and not record_all -> will still run but nothing recorded
                self.get_logger().warning('No topics declared and record_all is False -> recording will run but capture nothing.')
            else:
                cmd.extend(topics)

        if additional_args.strip():
            try:
                extra = shlex.split(additional_args)
                cmd.extend(extra)
            except Exception:
                # if shlex fails fallback to simple split
                cmd.extend(additional_args.strip().split())

        return cmd, out_path

    # ---------- start/stop operations ----------
    def start_recording(self):
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return False, 'already_recording'
            cmd, out_path = self._build_cmd()
            self.get_logger().info(f'Starting ros2 bag: {" ".join(cmd)}')
            try:
                # use process group so we can send signals to whole group
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid
                )
            except FileNotFoundError:
                self.get_logger().error('`ros2` executable not found. Make sure you sourced ROS 2 environment.')
                self._process = None
                return False, 'ros2_not_found'
            except Exception as e:
                self.get_logger().error(f'Failed to start ros2 bag: {e}')
                self._process = None
                return False, 'start_failed'

            # start background threads to log stdout/stderr
            self._stdout_thread = threading.Thread(target=self._stream_reader, args=(self._process.stdout, self.get_logger().info), daemon=True)
            self._stderr_thread = threading.Thread(target=self._stream_reader, args=(self._process.stderr, self.get_logger().error), daemon=True)
            self._stdout_thread.start()
            self._stderr_thread.start()

            # small delay to check process started
            time.sleep(0.2)
            if self._process.poll() is not None:
                code = self._process.returncode
                self.get_logger().error(f'ros2 bag process exited immediately with code {code}')
                self._process = None
                return False, f'exited_{code}'

            return True, out_path

    def stop_recording(self, timeout_sec=10.0):
        with self._lock:
            if self._process is None:
                return False, 'not_recording'
            pid = self._process.pid
            self.get_logger().info(f'Stopping ros2 bag pid={pid} (SIGINT)')
            try:
                # send SIGINT to process group (like Ctrl+C)
                os.killpg(os.getpgid(pid), signal.SIGINT)
            except Exception as e:
                self.get_logger().warn(f'Failed to send SIGINT: {e}')
            # wait for clean exit
            try:
                self._process.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                self.get_logger().warn('ros2 bag did not exit, sending SIGTERM')
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    self._process.wait(timeout=5.0)
                except Exception:
                    self.get_logger().warn('Sending SIGKILL')
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                    except Exception:
                        pass
            finally:
                # cleanup
                try:
                    if self._process.stdout:
                        self._process.stdout.close()
                    if self._process.stderr:
                        self._process.stderr.close()
                except Exception:
                    pass
                self._process = None
                return True, 'stopped'

    # ---------- service callbacks ----------
    def _srv_start_cb(self, request, response):
        ok, info = self.start_recording()
        response.success = bool(ok)
        response.message = str(info)
        return response

    def _srv_stop_cb(self, request, response):
        ok, info = self.stop_recording()
        response.success = bool(ok)
        response.message = str(info)
        return response

    def _srv_status_cb(self, request, response):
        running = (self._process is not None and self._process.poll() is None)
        response.success = running
        response.message = 'recording' if running else 'idle'
        return response

    # ---------- cmd topic ----------
    def _cmd_cb(self, msg):
        cmd = (msg.data or '').strip().lower()
        if cmd == 'start':
            ok, info = self.start_recording()
            self.get_logger().info(f'CMD start -> {ok}, {info}')
        elif cmd == 'stop':
            ok, info = self.stop_recording()
            self.get_logger().info(f'CMD stop -> {ok}, {info}')
        elif cmd == 'restart':
            self.get_logger().info('CMD restart')
            self.stop_recording()
            time.sleep(0.2)
            self.start_recording()
        else:
            self.get_logger().warn(f'Unknown cmd: "{msg.data}"')

    def _auto_start(self):
        ok, info = self.start_recording()
        if ok:
            self.get_logger().info(f'auto-started bag at: {info}')
        else:
            self.get_logger().error(f'auto-start failed: {info}')

def main(args=None):
    rclpy.init(args=args)
    node = RosbagRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('KeyboardInterrupt -> shutting down')
    finally:
        # ensure process stopped
        try:
            if node._process is not None:
                node.stop_recording()
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
