# Pendulum Simulation with Isaac ROS Vision Pipeline

A complete introduction to **NVIDIA Isaac ROS** using a simulated pendulum in **Gazebo Fortress (Ignition 6)**. The full stack — physics simulation, GPU-accelerated vision pipeline, and real-time bob detection — launches with a single command.

---

## What This Does

A pendulum swings left and right in Gazebo, driven by a square-wave torque controller. A fixed camera watches it. The raw camera feed is passed through the **Isaac ROS NITROS** zero-copy GPU pipeline where it gets rectified and encoded into a tensor. A color-based detector node then finds the red bob and draws a live bounding box around it.

```
Gazebo Physics + Camera
        ↓
/camera/image_raw          (640x480, 30Hz)
        ↓
Isaac ROS RectifyNode      GPU undistortion via NITROS
        ↓
/camera/image_rect         (640x480, undistorted)
        ↓
Isaac ROS DnnImageEncoder  normalize + resize to tensor
        ↓
/tensor_pub                (416x416 float32, TensorRT-ready)
        ↓
bob_detector node          OpenCV HSV color thresholding
        ↓
/bob_detection/image       annotated image with green bounding box
/bob_detection/detections  Detection2DArray with pixel coordinates
```

---

## System Requirements

| Component | Requirement |
|---|---|
| OS | Ubuntu 22.04 LTS (Jammy) |
| GPU | NVIDIA discrete GPU (tested: GTX 1650 Mobile, 4GB VRAM) |
| Driver | NVIDIA 535+ |
| CUDA | 12.2 |
| ROS 2 | Humble Hawksbill |
| Gazebo | Fortress / Ignition 6 |
| Isaac ROS | Release 3.0 |

> Isaac ROS requires an NVIDIA GPU. It does not run on CPU-only machines or integrated graphics.

> On hybrid AMD+NVIDIA laptops, run `sudo prime-select nvidia` before starting.

---

## Installation

### 1 — NVIDIA Driver

```bash
sudo apt install nvidia-driver-535
sudo reboot
nvidia-smi   # verify: should show your GPU and CUDA 12.2
```

### 2 — CUDA Toolkit 12.2

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-2

echo 'export PATH=/usr/local/cuda-12.2/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

nvcc --version   # verify: should say release 12.2
```

### 3 — ROS 2 Humble

```bash
sudo apt install software-properties-common curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu jammy main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list
sudo apt update
sudo apt install ros-humble-desktop
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc

ros2 topic list   # verify: returns /parameter_events and /rosout
```

### 4 — Gazebo Fortress + ROS Bridge

```bash
sudo apt install ros-humble-ros-gz \
                 ros-humble-ros-gz-bridge \
                 ros-humble-ros-gz-sim \
                 ros-humble-robot-state-publisher \
                 ros-humble-joint-state-publisher \
                 ros-humble-gz-ros2-control \
                 ros-humble-xacro

# Required: fix plugin search path
echo 'export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib:$GZ_SIM_SYSTEM_PLUGIN_PATH' >> ~/.bashrc
echo 'export IGN_GAZEBO_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib:$IGN_GAZEBO_SYSTEM_PLUGIN_PATH' >> ~/.bashrc
source ~/.bashrc

ign gazebo shapes.sdf   # verify: window with falling shapes opens
```

> If `gz sim` opens the wrong Gazebo, use `ign gazebo` instead. Both Gazebo Classic 11 and Fortress can coexist on Ubuntu 22.04 — the `gz` command defaults to Classic.

### 5 — Isaac ROS 3.0

```bash
# Add keyring
k="/usr/share/keyrings/nvidia-isaac-ros.gpg"
curl -fsSL https://isaac.download.nvidia.com/isaac-ros/repos.key | sudo gpg --dearmor | sudo tee $k > /dev/null

# Add repository
# release-3.0 is the last version supporting Ubuntu 22.04 + ROS 2 Humble
# Isaac ROS 4.x requires Ubuntu 24.04
f="/etc/apt/sources.list.d/nvidia-isaac-ros.list"
echo "deb [signed-by=$k] https://isaac.download.nvidia.com/isaac-ros/release-3 jammy release-3.0" | sudo tee $f

sudo apt update

sudo apt install ros-humble-isaac-ros-image-proc \
                 ros-humble-isaac-ros-nitros \
                 ros-humble-isaac-ros-tensor-rt \
                 ros-humble-isaac-ros-dnn-image-encoder
```

### 6 — VPI (Vision Programming Interface)

Isaac ROS depends on NVIDIA VPI which lives in a separate repository:

```bash
sudo apt install gnupg
sudo apt-key adv --fetch-key https://repo.download.nvidia.com/jetson/jetson-ota-public.asc
sudo add-apt-repository 'deb https://repo.download.nvidia.com/jetson/x86_64/jammy r36.2 main'
sudo apt update
sudo apt install libnvvpi3 vpi3-dev
```

### 7 — Python / OpenCV

```bash
sudo apt install ros-humble-cv-bridge \
                 ros-humble-vision-msgs \
                 python3-opencv
```

---

## Build

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone <this-repo> pendulum_sim

cd ~/ros2_ws
colcon build --packages-select pendulum_sim
source install/setup.bash
```

---

## Run

Everything launches with a single command:

```bash
ros2 launch pendulum_sim full_pipeline.launch.py
```

The launch is phased so each layer has time to initialise before the next starts:

| Time | What starts |
|---|---|
| 0s | Gazebo world, robot spawn, ROS bridge, effort controller |
| 5s | Isaac ROS rectify + encoder nodes (NITROS pipeline) |
| 8s | Pendulum oscillator (drives the swing) |
| 12s | Bob detector (bounding box) |

Then open the image viewer in a new terminal:

```bash
ros2 run rqt_image_view rqt_image_view
# Select /bob_detection/image from the dropdown
```

You should see the pendulum swinging with a green bounding box around the red bob, updating at 30Hz.

---

## Package Structure

```
pendulum_sim/
├── launch/
│   ├── full_pipeline.launch.py      ← single command launch (use this)
│   ├── pendulum_sim.launch.py       ← Gazebo simulation only
│   └── isaac_ros_vision.launch.py   ← Isaac ROS pipeline only
├── urdf/
│   └── pendulum.urdf                ← robot description + ros2_control
├── worlds/
│   └── pendulum.sdf                 ← Gazebo world + camera sensor
├── config/
│   └── controllers.yaml             ← effort controller config
├── pendulum_sim/
│   ├── __init__.py
│   ├── pendulum_oscillator.py       ← square wave torque publisher
│   └── bob_detector.py              ← OpenCV HSV detection + bounding box
├── setup.py
└── package.xml
```

---

## Topics

| Topic | Type | Description |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | Raw 640x480 feed at 30Hz |
| `/camera/image_raw/nitros` | NITROS | Zero-copy GPU version |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | Camera intrinsics |
| `/camera/image_rect` | `sensor_msgs/Image` | Rectified image from Isaac ROS |
| `/camera/image_rect/nitros` | NITROS | Zero-copy GPU version |
| `/tensor_pub` | `TensorList` | 416x416 float32 tensor |
| `/bob_detection/image` | `sensor_msgs/Image` | Annotated image with bounding box |
| `/bob_detection/detections` | `vision_msgs/Detection2DArray` | Bob bbox pixel coordinates |
| `/joint_states` | `sensor_msgs/JointState` | Ground truth pendulum angle |
| `/pivot_effort_controller/commands` | `std_msgs/Float64MultiArray` | Torque commands |

---

## Key Files Explained

### `pendulum.urdf`

Defines three links: `world` (fixed anchor), `rod` (grey cylinder), `bob` (red sphere, 1kg). The `pivot` revolute joint connects world to rod and swings on the **X axis** so the pendulum moves left-right when viewed from the front. Inertia values are physically accurate for the given geometry and mass.

Also contains the `ros2_control` block which wires the pivot joint to Gazebo's hardware plugin and exposes an effort command interface with ±10 Nm limits.

```xml
<axis xyz="1 0 0"/>  <!-- left-right swing from camera's point of view -->
```

### `pendulum.sdf`

The Gazebo world. Loads four system plugins: Physics, UserCommands, SceneBroadcaster, and Sensors (with ogre2 renderer — required for the camera to work). Has a green 100x100m ground plane and a static camera model.

Camera pose `0 3 1.2 0 0.1 -1.5707` means: centred, 3m in front, 1.2m high, slight downward tilt, facing the pendulum. The `<pose>` must be on the `<model>` element, not `<link>` — this is a common mistake.

### `controllers.yaml`

Configures `ros2_control` with a 20Hz update rate and an `effort_controllers/JointGroupEffortController` on the `pivot` joint. This is what makes `/pivot_effort_controller/commands` available as a torque input.

### `pendulum_oscillator.py`

Publishes a square-wave torque at 20Hz. Uses `math.sin` to alternate between `+3 Nm` and `-3 Nm` with a 1-second period. This drives the pendulum into sustained left-right oscillation within its ±90° joint limits.

### `bob_detector.py`

Subscribes to `/camera/image_rect`. Converts each frame to HSV and applies two red masks — red wraps around the HSV hue wheel at 0°/360° so two ranges (`[0–10]` and `[170–180]`) are needed to catch it reliably. Morphological open+close removes noise. The largest contour above 100px² is treated as the bob. A green bounding box and pixel coordinates are drawn on the frame and published to `/bob_detection/image`. Structured detections are also published as `Detection2DArray` on `/bob_detection/detections`.

### `full_pipeline.launch.py`

Uses `TimerAction` to sequence four phases. All Isaac ROS nodes run in one `ComposableNodeContainer` with `component_container_mt` (multi-threaded). This is required — NITROS format negotiation fails if the rectify and encoder nodes are in separate containers.

---

## Isaac ROS Concepts

### NITROS — Zero-Copy GPU Transport

Standard ROS 2 copies image data between nodes via CPU serialization. NITROS passes a GPU buffer pointer directly, eliminating the copy entirely:

```
Standard:  GPU → CPU (serialize) → CPU (deserialize) → GPU   ~several ms
NITROS:    GPU → GPU (pointer handoff)                        ~zero overhead
```

The `/nitros` topic variants in `ros2 topic list` are the NITROS transport operating in parallel with standard ROS topics. Both are available simultaneously — standard topics for tools like rqt, NITROS for inter-node GPU transfer.

### Composable Node Container

Isaac ROS nodes are composable components loaded into a shared container process. Intra-process communication and NITROS negotiation both require nodes to share the same container:

```python
ComposableNodeContainer(
    name='vision_container',
    executable='component_container_mt',
    composable_node_descriptions=[
        rectify_node,    # shares process memory with encoder
        encoder_node,
    ]
)
```

### GXF — Graph Execution Framework

The underlying runtime for Isaac ROS. When nodes load, GXF compiles and optimizes a computation graph. A few seconds of startup delay is normal — this is GXF building the graph, not a hang.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `libgz_ros2_control-system.so not found` | Plugin path missing | Add `GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib` to `.bashrc` |
| `libnvvpi.so.3 not found` | VPI not installed | Install `libnvvpi3` from NVIDIA Jetson repo (step 6) |
| `Could not negotiate` (NITROS) | Nodes in separate containers | Put all Isaac ROS nodes in one `ComposableNodeContainer` |
| `gz sim` opens Gazebo Classic | Command conflict with Classic 11 | Use `ign gazebo` instead of `gz sim` |
| Camera topic absent from `ign topic -l` | Sensors plugin missing from SDF | Add `gz-sim-sensors-system` plugin to world |
| Only green ground visible in rqt | Camera `<pose>` on wrong XML level | Move `<pose>` inside `<model>`, not `<link>` |
| `Invalid input_image_width` | Wrong encoder parameter name | Add `input_image_width` and `input_image_height` params |
| Encoder container empty after launch | GXF init race condition | Run rectify and encoder in the same container |
| `pendulum_oscillator` executable not found | Wrong entry point in `setup.py` | Set `pendulum_sim.pendulum_oscillator:main` |

---

## Verified Checkpoints

- [x] `nvidia-smi` shows GPU + CUDA 12.2
- [x] `nvcc --version` confirms CUDA toolkit
- [x] `ros2 topic list` runs without errors
- [x] `ign gazebo shapes.sdf` opens a window
- [x] Pendulum spawns, swings, camera streams at 30Hz
- [x] `/camera/image_raw/nitros` appears (NITROS active)
- [x] `/tensor_pub` publishes at 30Hz
- [x] Green bounding box tracks red bob in rqt

---

## Next Steps

- Replace color detection with a **TensorRT YOLO model** loaded via `isaac_ros_tensor_rt`
- Map bob pixel coordinates to pendulum angle, compare against `/joint_states` ground truth
- Close the control loop — feed detection output back into the effort controller
- Record a rosbag and replay for offline analysis

---

## Built With

Ubuntu 22.04 · ROS 2 Humble · Gazebo Fortress · Isaac ROS 3.0 · CUDA 12.2 · OpenCV · NITROS