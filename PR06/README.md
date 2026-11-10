# PR06: Ackermann model, tf2 and transform QoS

Work directory: `/home/a-god/robotics/PR06`, WSL Ubuntu-24.04, ROS 2 Jazzy.
Official assignment: https://ros.lms.ci.nsu.ru/practices/pr06

## Build and verify

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=47
colcon build --symlink-install --packages-select course_description
source install/setup.bash
xacro src/course_description/urdf/vehicle.urdf.xacro > /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
colcon test --packages-select course_description --event-handlers console_direct+
colcon test-result --verbose
```

Dependencies: Jazzy desktop, xacro, robot_state_publisher, tf2_ros, tf2_tools,
liburdfdom-tools, graphviz, ament_cmake_pytest, pytest, NumPy and PyYAML.
Optional X11 capture uses Pillow and libXcomposite. No Gazebo or
joint_state_publisher package is required. Source both setup files in new terminals.

## Display and parameters

```bash
ros2 launch course_description display.launch.py rviz:=true demo_joints:=true
```

RViz uses Fixed Frame `base_link`, RobotModel and TF. All TF edges belong to
robot_state_publisher. The optional demo node publishes only zero-valued
`joint_states` at 10 Hz; it is not a controller or a dynamics simulator.
Without it the three fixed sensors are immediately available; six movable
joint transforms appear only after joint states arrive.

Launch defaults: `rviz:=false`, `demo_joints:=false`. Geometry arguments are
`wheelbase`, `track`, `wheel_radius`, with defaults from config/dimensions.yaml.
They also work directly in xacro, e.g. `wheelbase:=1.2 track:=0.8 wheel_radius:=0.16`.

## Source geometry and frames

The unchanged SDF is in `src/course_description/reference/model.sdf` for independent
tests; its SHA256 is in config/dimensions.yaml. Gazebo plugins are not imported.

| Property | SI value |
| --- | --- |
| Wheelbase / track | 0.80 / 0.62 m |
| Wheel radius / width | 0.12 / 0.07 m |
| Body size | 1.05 x 0.52 x 0.22 m |
| Body geometry center | (0, 0, 0.12) m |
| Camera, lidar, IMU (each) | (0.28, 0, 0.38) m; zero RPY |
| Steering limits | +/-0.55 rad; effort 25 N m |

All three sensors are colocated in the source; their RViz labels overlap by design.
SDF defines no sensor or knuckle housing sizes: these links have inertia and TF
axes without invented visual/collision geometry. The body and four wheels each
have separate visual and collision definitions.

REP-103 axes are +X forward, +Y left, +Z up. Wheel joint frames use these axes;
cylinder geometry is rolled pi/2 about X, matching the physical SDF orientation.
Rolling axes are +Y and steering axes +Z. The SDF global spawn z=0.18 is world
placement, not part of local TF. Camera_link uses body axes; no optical image
stream is published here.

Masses come from SDF. Body/wheel inertia is calculated for uniform solids about
their geometric centers; wheel inertia updates with radius. Sensor/knuckle
tensors are retained. Tests check positivity and principal-moment inequalities.
The steering velocity bound 1 rad/s is an explicit conservative assumption;
SDF has no velocity bound. KDL warns that it ignores root-link inertia in its
kinematic parser; the valid inertia remains in URDF and does not affect TF.

## Repeat real checks

```bash
python3 -u scripts/check_pr06.py --output /tmp/pr06-new-run --rviz
```

Use a new output directory. Omit `--rviz` on headless CI. The script starts one
RSP and connects late RELIABLE subscribers with TRANSIENT_LOCAL and VOLATILE
durability to the SAME publisher, requiring exit 0 and 124 respectively.
It checks unchanged publisher GID and no new static sample, enables demo joints,
checks wheel TF, runs tf2_echo/view_frames, captures the real RViz X11 backing
pixmap if requested, and stops all its processes.

## Defect and evidence

Changing only lidar's parent from base_link to camera_link preserves its local
offset but shifts its absolute position from (0.28, 0, 0.38) to (0.56, 0, 0.76).
check_urdf accepts that tree; the parent/geometry test fails. The same test and
live measurement are repeated on the correct implementation.

The defect commit is preserved on PR06-defect and in evidence/pr06/defect.bundle,
with its patch, SHA and commands in defect-provenance.json. Recover it after cloning:

```bash
git fetch evidence/pr06/defect.bundle PR06-defect:PR06-defect
```

Implementation commit A precedes final evidence; report.json references A.
Commit B contains evidence and the AI declaration. The unchanged course kit is
v1-w07, archive SHA256 `9b7fdd5424d3d97e47d51dbe23064934585e62135dc2902844dd679529bda929`.

```bash
python3 .course-kit/v1/tools/check_practice.py PR06 --submission .
```

GitHub workflow `.github/workflows/pr06.yml` repeats build, tests, live TF/QoS
and the evidence contract. Local RViz verification and remote CI are reported separately.
