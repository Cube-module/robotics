# PR06 frames and publication ownership

Units: metres and radians; REP-103: +X forward, +Y left, +Z up.

Root: `base_link`, at the axle-plane origin; it has no incoming transform.

| Joint | Parent | Child | Type | XYZ at zero joint position | RPY | TF owner |
| --- | --- | --- | --- | --- | --- | --- |
| front_left_steering_joint | base_link | front_left_knuckle | revolute | 0.4 0.31 0 | 0 0 0 | robot_state_publisher: /tf (requires joint_states) |
| front_left_wheel_joint | front_left_knuckle | front_left_wheel | continuous | 0 0 0 | 0 0 0 | robot_state_publisher: /tf (requires joint_states) |
| front_right_steering_joint | base_link | front_right_knuckle | revolute | 0.4 -0.31 0 | 0 0 0 | robot_state_publisher: /tf (requires joint_states) |
| front_right_wheel_joint | front_right_knuckle | front_right_wheel | continuous | 0 0 0 | 0 0 0 | robot_state_publisher: /tf (requires joint_states) |
| rear_left_wheel_joint | base_link | rear_left_wheel | continuous | -0.4 0.31 0 | 0 0 0 | robot_state_publisher: /tf (requires joint_states) |
| rear_right_wheel_joint | base_link | rear_right_wheel | continuous | -0.4 -0.31 0 | 0 0 0 | robot_state_publisher: /tf (requires joint_states) |
| camera_joint | base_link | camera_link | fixed | 0.28 0.0 0.38 | 0.0 0.0 0.0 | robot_state_publisher: /tf_static |
| lidar_joint | base_link | lidar_link | fixed | 0.28 0.0 0.38 | 0.0 0.0 0.0 | robot_state_publisher: /tf_static |
| imu_joint | base_link | imu_link | fixed | 0.28 0.0 0.38 | 0.0 0.0 0.0 | robot_state_publisher: /tf_static |

The demo node publishes only joint_states, never TF. No second TF owner is launched.
Wheel visual/collision geometry is rolled pi/2 around X; the wheel joint frame itself remains REP-103 aligned.
Camera, lidar and IMU share (0.28, 0, 0.38) and zero RPY in the source SDF. No arbitrary sensor offsets were introduced.
The source model world spawn height 0.18 m is not a local robot transform.

Geometry is checked against the unchanged reference/model.sdf by test_model.py.
Defect: changing only lidar parent to camera_link gives base_link -> lidar_link = (0.56, 0, 0.76).
defect-test.txt/defect-tf.txt prove the failure and displacement; fixed-test.txt/fixed-tf.txt prove the correction.

RViz screenshot rviz.png was visually inspected: Global Status: Ok, RobotModel/TF enabled, base_link view and correctly positioned body/wheels.
