import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
import math

class PendulumOscillator(Node):
    def __init__(self):
        super().__init__('pendulum_oscillator')
        self.pub = self.create_publisher(
            Float64MultiArray,
            '/pivot_effort_controller/commands',
            10
        )
        self.t = 0.0
        self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz

    def timer_callback(self):
        msg = Float64MultiArray()
        period = 1.0
        torque = 3.0 if math.sin(2 * math.pi * self.t / period) >= 0 else -3.0
        msg.data = [torque]
        self.pub.publish(msg)
        self.t += 0.05

def main():
    rclpy.init()
    node = PendulumOscillator()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()