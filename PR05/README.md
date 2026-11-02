# PR05: Launch, QoS and bag replay

ROS 2 Jazzy / Ubuntu 24.04 / WSL2. Run all commands in
`/home/a-god/robotics/PR05`. The `patrol` package and its tests are copied
unchanged from PR04 (commit 4616fca).

## Build and tests

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=47
colcon build --symlink-install
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

Dependencies: ROS Jazzy desktop (turtlesim, rclpy, launch, rosbag2 with MCAP),
colcon, pytest, ament_flake8, ament_pep257, ament_copyright and python3-yaml.
Use the same ROS_DOMAIN_ID in every experiment terminal; it is not hardcoded
in the nodes. In a new terminal source both setup.bash files again.

## Live system

```bash
ros2 launch course_bringup patrol.launch.py namespace:=robot_a subscriber_reliability:=reliable record:=false
```

This starts one global `/turtlesim` and `/robot_a/{patrol,pose_relay,pose_subscriber}`.
Patrol still reads `/turtle1/pose`; its relative `cmd_vel` is remapped to
`/turtle1/cmd_vel`. Relay forwards each original Pose to `sensor_pose` with
BEST_EFFORT. The subscriber parameter is read-only after startup: restart the
launch to change its QoS. Its once-per-second log shows the actual receive count.

In another sourced terminal:

```bash
ros2 topic list
ros2 topic info /robot_a/sensor_pose --verbose
timeout 3s ros2 topic echo /robot_a/sensor_pose turtlesim/msg/Pose --qos-reliability reliable --once
```

The topic exists but RELIABLE requests cannot match the BEST_EFFORT offer.
The expected timeout returns 124 and no Pose. Stop launch with Ctrl+C and restart:

```bash
ros2 launch course_bringup patrol.launch.py namespace:=robot_a subscriber_reliability:=best_effort record:=false
```

```bash
timeout 3s ros2 topic echo /robot_a/sensor_pose turtlesim/msg/Pose --qos-reliability best_effort --once
```

The explicit message type avoids spending the short timeout on type discovery.
All four launch arguments are listed by `ros2 launch course_bringup patrol.launch.py --show-args`:

| Argument | Default | Meaning |
| --- | --- | --- |
| namespace | robot_a | Namespace for patrol, relay and subscriber |
| subscriber_reliability | best_effort | reliable reproduces the defect |
| record | false | Start the MCAP recorder only if true |
| bag_dir | evidence/pr05/launch-bag | New directory for the recorder |

## Record and replay

With the fixed live launch running, record into a NEW directory:

```bash
ros2 bag record -s mcap -o /tmp/pr05-new-bag --topics /robot_a/sensor_pose
```

After collecting messages, use Ctrl+C to finalize metadata. Stop the live launch
before playback. Then:

```bash
ros2 bag info /tmp/pr05-new-bag
ros2 bag play /tmp/pr05-new-bag --qos-profile-overrides-path config/qos-overrides.yaml
```

In another terminal run the BEST_EFFORT echo above, or:

```bash
ros2 run course_bringup pose_subscriber --ros-args -r __ns:=/robot_a -p subscriber_reliability:=best_effort
```

The override is keyed by the full `/robot_a/sensor_pose` name. For another
namespace, create a corresponding override entry. Launch recording resolves
its topic from the namespace argument automatically:

```bash
ros2 launch course_bringup patrol.launch.py namespace:=robot_a subscriber_reliability:=best_effort record:=true bag_dir:=/tmp/pr05-new-launch-bag
```

## Repeat the complete experiment

```bash
QT_QPA_PLATFORM=offscreen python3 -u scripts/check_pr05.py --output /tmp/pr05-new-run
```

The output directory must not already exist. The script preserves every CLI
attempt, checks real endpoints, requires the incompatible echo to return 124,
records an MCAP bag, stops the live source, and verifies that rosbag2_player is
the sole replay publisher with BEST_EFFORT. It also checks launch recording,
`record:=false`, a second namespace and SIGINT cleanup. Offscreen only hides
the turtlesim window; the actual simulator and ROS graph run normally.
Discovery queries retry at 2, 4 and 8 seconds; all attempts remain in the logs.
No other simulator should run in the selected domain during these checks.

## Submitted evidence

`evidence/pr05/` contains the real final logs, both MCAP recordings, their
metadata, test outputs and report.json. The mandatory bag-metadata.yaml is a
byte-for-byte copy of bag/metadata.yaml. qos-before.txt includes the timeout
and zero-count subscriber log; qos-after.txt includes live/replay messages,
endpoint diagnostics, bag info and subscriber logs.

The unchanged course-kit v1-w07 is reused from PR04. Verify it and the report:

```bash
sha256sum .course-kit/course-kit.tar.gz
python3 .course-kit/v1/tools/check_practice.py PR05 --submission .
```

Expected archive SHA256:
`9b7fdd5424d3d97e47d51dbe23064934585e62135dc2902844dd679529bda929`.
The checker verifies the evidence contract; real functionality is additionally
checked by colcon and scripts/check_pr05.py. Implementation commit A precedes
the final experiment; report.commit references A; evidence is committed in B.
Local course-kit/build/install/log directories are ignored by Git.
