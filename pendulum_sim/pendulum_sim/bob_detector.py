import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray, Detection2D, BoundingBox2D
from cv_bridge import CvBridge
import cv2
import numpy as np

class BobDetectorNode(Node):

    def __init__(self):
        super().__init__('bob_detector')
        self.bridge = CvBridge()

        # Subscribe to rectified image
        self.sub = self.create_subscription(
            Image,
            '/camera/image_rect',
            self.image_callback,
            10
        )

        # Publish annotated image
        self.image_pub = self.create_publisher(
            Image,
            '/bob_detection/image',
            10
        )

        # Publish detections
        self.detection_pub = self.create_publisher(
            Detection2DArray,
            '/bob_detection/detections',
            10
        )

        self.get_logger().info('Bob detector node started')

    def image_callback(self, msg):
        # Convert ROS image to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Red color range in HSV
        # Red wraps around in HSV so we need two ranges
        lower_red1 = np.array([0,   120, 70])
        upper_red1 = np.array([10,  255, 255])
        lower_red2 = np.array([170, 120, 70])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask  = cv2.bitwise_or(mask1, mask2)

        # Remove noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        detection_array = Detection2DArray()
        detection_array.header = msg.header

        if contours:
            # Pick the largest contour (the bob)
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)

            # Filter out tiny blobs
            if area > 100:
                x, y, w, h = cv2.boundingRect(largest)

                # Draw bounding box on frame
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(
                    frame, f'Bob ({x+w//2},{y+h//2})',
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2
                )

                # Build Detection2D message
                det = Detection2D()
                det.header = msg.header
                bbox = BoundingBox2D()
                bbox.center.position.x = float(x + w // 2)
                bbox.center.position.y = float(y + h // 2)
                bbox.size_x = float(w)
                bbox.size_y = float(h)
                det.bbox = bbox
                detection_array.detections.append(det)

                self.get_logger().info(
                    f'Bob detected at ({x+w//2}, {y+h//2}) '
                    f'size={w}x{h} area={area:.0f}',
                    throttle_duration_sec=1.0
                )
            else:
                self.get_logger().warn(
                    'Red blob too small, skipping',
                    throttle_duration_sec=2.0
                )
        else:
            self.get_logger().warn(
                'Bob not detected',
                throttle_duration_sec=2.0
            )

        # Publish annotated image
        self.image_pub.publish(
            self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        )

        # Publish detections
        self.detection_pub.publish(detection_array)


def main(args=None):
    rclpy.init(args=args)
    node = BobDetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()