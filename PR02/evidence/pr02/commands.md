# PR02 commands

```bash
ros2 pkg create --build-type ament_python turtle_bringup
colcon build --symlink-install --packages-select turtle_bringup
source install/setup.bash
ros2 pkg prefix turtle_bringup
ros2 launch turtle_bringup sim.launch.py
ros2 node list
ros2 topic echo /turtle1/pose --once

ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'

ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'

ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose

ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'

python3 -m py_compile src/turtle_bringup/launch/sim.launch.py
(cd src/turtle_bringup && python3 -m pytest test -q)
```