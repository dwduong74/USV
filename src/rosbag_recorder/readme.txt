# start
ros2 service call /rosbag_recorder/start std_srvs/srv/Trigger "{}"

# stop
ros2 service call /rosbag_recorder/stop std_srvs/srv/Trigger "{}"

# check trạng thái
ros2 service call /rosbag_recorder/status std_srvs/srv/Trigger "{}"


ros2 topic pub /rosbag_recorder/cmd std_msgs/String "data: 'start'"
ros2 topic pub /rosbag_recorder/cmd std_msgs/String "data: 'stop'"


ros2 run <your_package> rosbag_recorder \
  --ros-args -p topics:="['/camera/image_raw','/tf']" -p output_dir:="/home/you/recordings" -p bag_prefix:="test" -p additional_args:="--compression-mode file --compression-format zstd"


from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='your_package',
            executable='rosbag_recorder',
            name='rosbag_recorder',
            parameters=[{
                'topics': ['/camera/image_raw', '/tf'],
                'output_dir': '/tmp/rosbags',
                'bag_prefix': 'run1',
                'additional_args': '--compression-mode file --compression-format zstd',
                'auto_start': True,
                'start_delay': 1.0,
            }]
        )
    ])



Node(
    package='your_package',
    executable='rosbag_recorder',
    name='rosbag_recorder',
    parameters=[{
        'record_all': True,
        'output_dir': '/tmp/rosbags',
        'bag_prefix': 'full_record',
        'auto_start': True
    }]
)



ros2 bag record -o <bag_path> -a


ros2 run your_package rosbag_recorder \
  --ros-args -p record_all:=true
