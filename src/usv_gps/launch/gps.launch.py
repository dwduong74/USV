from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='usv_gps',
            executable='gps_node',
            name='gps_ekf_node',
            output='screen',
            emulate_tty=True,
        )
    ])
