from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

def generate_launch_description():

    return LaunchDescription([
        ComposableNodeContainer(
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
        ),
    ])