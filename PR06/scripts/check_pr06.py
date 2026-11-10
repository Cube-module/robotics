#!/usr/bin/env python3
"""Collect real TF/QoS evidence, and optionally capture the live RViz window."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformListener


class Experiment:
    def __init__(self, output, rviz):
        self.output, self.rviz = output, rviz
        self.children = []
        self.commands = []
        self.node = rclpy.create_node('pr06_verifier')
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self.node)
        self.static_samples = []
        self.node.create_subscription(TFMessage, '/tf_static', self.static_samples.append,
                                      QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                                 durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.result = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
                       'domain': os.environ.get('ROS_DOMAIN_ID', '0'), 'checks': {}}

    def wait(self, predicate, seconds=15):
        deadline = time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)
        assert predicate(), 'Timed out waiting for ROS graph/TF'

    def spin_for(self, seconds):
        deadline = time.monotonic()+seconds
        while time.monotonic()<deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def command(self, args, filename, expected=0, cwd=None):
        self.commands.append(shlex.join(args))
        print('$', shlex.join(args), flush=True)
        result = subprocess.run(args, capture_output=True, text=True, timeout=30, cwd=cwd)
        with (self.output/filename).open('a') as stream:
            stream.write('$ '+shlex.join(args)+'\n'+result.stdout+result.stderr)
            stream.write(f'\nexit_code={result.returncode}\n\n')
        assert expected is None or result.returncode == expected, (args, result.returncode, result.stdout, result.stderr)
        return result

    def query(self, topic, filename):
        for seconds in (2,4,8):
            result = self.command(['ros2','topic','info',topic,'--verbose','--no-daemon',
                                   '--spin-time',str(seconds)], filename, expected=None)
            if result.returncode == 0 and 'robot_state_publisher' in result.stdout:
                return result.stdout
            assert result.returncode == 0 or result.stderr.strip().startswith('Unknown topic'), result.stderr
        raise AssertionError('No publisher discovered: '+topic)

    def start(self, args, filename):
        stream = (self.output/filename).open('w')
        stream.write('$ '+shlex.join(args)+'\n'); stream.flush()
        self.commands.append(shlex.join(args))
        child = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        item = (child, stream, self.output/filename)
        self.children.append(item)
        return item

    def stop(self, item):
        child, stream, path = item
        if stream.closed:
            return
        try:
            if child.poll() is None:
                if child.args[:2] == ['ros2','run']:
                    os.killpg(child.pid, signal.SIGINT)
                else:
                    child.send_signal(signal.SIGINT)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL); child.wait()
                    raise AssertionError('SIGINT cleanup failed')
        finally:
            stream.write(f'\nexit_code={child.returncode}\n'); stream.close()
        text = path.read_text()
        assert child.returncode == 0, text
        assert 'Traceback' not in text and 'process has died' not in text, text

    def publishers(self, topic='/tf_static'):
        return self.node.get_publishers_info_by_topic(topic)

    def pose(self, frame):
        return self.buffer.lookup_transform('base_link',frame,Time()).transform

    def screenshot(self):
        # WSLg redirects X11 surfaces; QScreen.grabWindow can return a black image.
        self.command(['python3', str(Path(__file__).with_name('capture_rviz.py')),
                      str(self.output/'rviz.png')], 'rviz-capture.txt')
        self.result['rviz_screenshot'] = 'rviz.png'

    def run(self):
        self.spin_for(2)
        assert not self.publishers(), 'Existing /tf_static publisher would contaminate the experiment'
        launch = self.start(['ros2','launch','course_description','display.launch.py',
                             'rviz:='+str(self.rviz).lower(),'demo_joints:=false'], 'launch.log')
        self.wait(lambda: len(self.publishers())==1 and self.static_samples
                  and self.buffer.can_transform('base_link','lidar_link',Time()))
        self.spin_for(2)
        pub = self.publishers()[0]
        assert pub.node_name == 'robot_state_publisher'
        assert pub.qos_profile.reliability == ReliabilityPolicy.RELIABLE
        assert pub.qos_profile.durability == DurabilityPolicy.TRANSIENT_LOCAL
        gid = list(pub.endpoint_gid)
        samples = len(self.static_samples)
        assert samples == 1
        assert {t.child_frame_id for t in self.static_samples[0].transforms} == {
            'camera_link','lidar_link','imu_link'}
        self.query('/tf_static','tf-qos.txt')
        transient = self.command(['timeout','4','ros2','topic','echo','/tf_static',
                                  'tf2_msgs/msg/TFMessage','--once','--qos-durability',
                                  'transient_local','--qos-reliability','reliable'], 'tf-qos.txt')
        assert 'lidar_link' in transient.stdout
        volatile = self.command(['timeout','4','ros2','topic','echo','/tf_static',
                                 'tf2_msgs/msg/TFMessage','--once','--qos-durability',
                                 'volatile','--qos-reliability','reliable'], 'tf-qos.txt', expected=124)
        assert 'transforms:' not in volatile.stdout
        self.spin_for(1)
        assert len(self.publishers())==1 and list(self.publishers()[0].endpoint_gid)==gid
        assert len(self.static_samples)==samples
        assert launch[0].poll() is None
        self.result.update({'static_publisher_gid':gid,'static_samples_before':samples,
                            'static_samples_after':len(self.static_samples),
                            'transient_local_exit':transient.returncode,
                            'volatile_exit':volatile.returncode})
        self.result['checks']['late_subscriber_qos'] = True
        for frame in ('camera_link','lidar_link','imu_link'):
            tf = self.pose(frame)
            assert all(math.isclose(a,b,abs_tol=1e-9) for a,b in zip(
                [tf.translation.x,tf.translation.y,tf.translation.z], [0.28,0,0.38]))
            assert math.isclose(abs(tf.rotation.w),1.0,abs_tol=1e-9)
        echo = self.command(['timeout','10','ros2','run','tf2_ros','tf2_echo',
                             'base_link','lidar_link'], 'model-check.txt', expected=124)
        assert '0.280' in echo.stdout and '0.380' in echo.stdout
        self.result['checks']['fixed_tf_without_joint_states'] = True
        demo = self.start(['ros2','run','course_description','demo_joint_states.py'], 'joint-states.log')
        wheels = ['front_left_wheel','front_right_wheel','rear_left_wheel','rear_right_wheel']
        self.wait(lambda: all(self.buffer.can_transform('base_link',f,Time()) for f in wheels))
        for frame in wheels:
            tf = self.pose(frame)
            assert math.isclose(tf.translation.x,0.4 if frame.startswith('front') else -0.4,abs_tol=1e-9)
            assert math.isclose(tf.translation.y,0.31 if 'left' in frame else -0.31,abs_tol=1e-9)
        self.wait(lambda: len(self.publishers('/tf'))==1)
        assert self.publishers('/tf')[0].node_name=='robot_state_publisher'
        assert self.publishers('/tf')[0].qos_profile.durability==DurabilityPolicy.VOLATILE
        self.query('/tf','tf-qos.txt')
        self.command(['ros2','run','tf2_tools','view_frames'], 'model-check.txt', cwd=self.output)
        self.result['checks']['dynamic_tf_and_single_owner'] = True
        if self.rviz:
            self.spin_for(4)
            assert launch[0].poll() is None
            self.screenshot()
        self.stop(demo)
        self.stop(launch)
        self.wait(lambda: not self.publishers())
        self.result['checks']['clean_shutdown'] = True
        with (self.output/'tf-qos.txt').open('a') as stream:
            stream.write('The /tf_static publisher is RELIABLE + TRANSIENT_LOCAL. A late reliable '
                         'TRANSIENT_LOCAL reader receives its retained fixed transforms (exit 0). '
                         'A late reliable VOLATILE reader receives no old samples (exit 124). '
                         'The publisher GID was unchanged and our original observer received '
                         'exactly one static sample throughout both attempts. /tf carries '
                         'changing joint transforms with VOLATILE durability; the actual '
                         'endpoint profile is recorded above. Only robot_state_publisher owns TF.\n')
        self.result['commands']=self.commands
        self.result['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        (self.output/'runtime.json').write_text(json.dumps(self.result,indent=2)+'\n')
        print(json.dumps(self.result,indent=2),flush=True)

    def close(self):
        errors=[]
        for item in reversed(self.children):
            try:
                self.stop(item)
            except Exception as error:
                errors.append(str(error))
        self.node.destroy_node()
        if errors:
            raise AssertionError('\n'.join(errors))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rviz',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    rclpy.init()
    experiment=Experiment(args.output.resolve(),args.rviz)
    try:
        experiment.run()
    finally:
        try:
            experiment.close()
        finally:
            rclpy.try_shutdown()


if __name__=='__main__':
    main()
