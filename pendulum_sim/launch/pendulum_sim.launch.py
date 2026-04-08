import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_dir    = get_package_share_directory('pendulum_sim')
    urdf_path  = os.path.join(pkg_dir, 'urdf',   'pendulum.urdf')
    world_path = os.path.join(pkg_dir, 'worlds',  'pendulum.sdf')
    controllers_yaml = os.path.join(pkg_dir, 'config', 'controllers.yaml')

    with open(urdf_path, 'r') as f:
        robot_description = f.read().replace(
            '$(find pendulum_sim)/config/controllers.yaml',
            controllers_yaml  # ← resolves to full absolute path at launch time
        )
    print("== PATCHED URDF ==")
    print(robot_description)
    print("== END URDF ==")

    return LaunchDescription([
        # 1. Launch Gazebo with our world
        ExecuteProcess(
            cmd=['ign', 'gazebo', world_path, '-r'],
            output='screen'
        ),

        # 2. Spawn the pendulum into Gazebo
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', 'pendulum',
                '-string', robot_description,  # ← pass patched URDF string, not file
                '-z', '0.0',
            ],
            output='screen'
        ),

        # 3. Robot state publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen'
        ),

        # 4. Spawn the effort controller
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=['pivot_effort_controller'],
            output='screen'
        ),
        # 5. Bridge camera topic from Gazebo → ROS 2
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/camera/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image',
                '/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            ],
            output='screen'
        ),
    ])
        