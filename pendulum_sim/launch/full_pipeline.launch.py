import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    pkg_dir          = get_package_share_directory('pendulum_sim')
    urdf_path        = os.path.join(pkg_dir, 'urdf',   'pendulum.urdf')
    world_path       = os.path.join(pkg_dir, 'worlds',  'pendulum.sdf')
    controllers_yaml = os.path.join(pkg_dir, 'config',  'controllers.yaml')

    with open(urdf_path, 'r') as f:
        robot_description = f.read().replace(
            '$(find pendulum_sim)/config/controllers.yaml',
            controllers_yaml
        )

    # ================================================================
    # PHASE 1 — Simulation (starts immediately)
    # ================================================================

    gazebo = ExecuteProcess(
        cmd=['ign', 'gazebo', world_path, '-r'],
        output='screen'
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'pendulum',
            '-string', robot_description,
            '-z', '0.0',
        ],
        output='screen'
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen'
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/camera/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
        ],
        output='screen'
    )

    effort_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['pivot_effort_controller'],
        output='screen'
    )

    # ================================================================
    # PHASE 2 — Isaac ROS vision pipeline (delayed 5s)
    # ================================================================

    isaac_ros_pipeline = ComposableNodeContainer(
        name='vision_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        composable_node_descriptions=[

            ComposableNode(
                package='isaac_ros_image_proc',
                plugin='nvidia::isaac_ros::image_proc::RectifyNode',
                name='rectify_node',
                parameters=[{
                    'output_width':  640,
                    'output_height': 480,
                }],
                remappings=[
                    ('image_raw',   '/camera/image_raw'),
                    ('camera_info', '/camera/camera_info'),
                    ('image_rect',  '/camera/image_rect'),
                ],
            ),

            ComposableNode(
                package='isaac_ros_dnn_image_encoder',
                plugin='nvidia::isaac_ros::dnn_inference::DnnImageEncoderNode',
                name='encoder_node',
                parameters=[{
                    'input_image_width':    640,
                    'input_image_height':   480,
                    'network_image_width':  416,
                    'network_image_height': 416,
                    'image_mean':   [0.5, 0.5, 0.5],
                    'image_stddev': [0.5, 0.5, 0.5],
                    'num_blocks':   40,
                }],
                remappings=[
                    ('image',          '/camera/image_rect'),
                    ('encoded_tensor', '/tensor_pub'),
                ],
            ),

        ],
        output='screen',
    )

    # ================================================================
    # PHASE 3 — Pendulum oscillator (delayed 8s)
    # ================================================================

    pendulum_oscillator = Node(
        package='pendulum_sim',
        executable='pendulum_oscillator',
        name='pendulum_oscillator',
        output='screen'
    )

    # ================================================================
    # PHASE 4 — Bob detector (delayed 12s)
    # ================================================================

    bob_detector = Node(
        package='pendulum_sim',
        executable='bob_detector',
        name='bob_detector',
        output='screen'
    )

    # ================================================================
    # Launch sequence
    # ================================================================

    return LaunchDescription([

        # Phase 1 — immediate
        gazebo,
        spawn_robot,
        robot_state_publisher,
        bridge,
        effort_controller,

        # Phase 2 — Isaac ROS after 5 seconds
        TimerAction(period=5.0,  actions=[isaac_ros_pipeline]),

        # Phase 3 — Oscillator after 8 seconds
        TimerAction(period=8.0,  actions=[pendulum_oscillator]),

        # Phase 4 — Bob detector after 12 seconds
        TimerAction(period=12.0, actions=[bob_detector]),

    ])