#!/usr/bin/env python3
"""Measure a model's actual lidar transform in an isolated RSP process."""
import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import tempfile
import yaml
import rclpy
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model',type=Path,required=True)
parser.add_argument('--x',type=float,required=True)
parser.add_argument('--z',type=float,required=True)
args=parser.parse_args()
command=['xacro',str(args.model)]
print('$', ' '.join(command),flush=True)
xml=subprocess.check_output(command,text=True)
rclpy.init()
node=rclpy.create_node('pr06_transform_probe')
buffer=Buffer(); listener=TransformListener(buffer,node)
temporary=tempfile.TemporaryDirectory(prefix='pr06-transform-')
params=Path(temporary.name)/'params.yaml'
params.write_text(yaml.safe_dump({'/**':{'ros__parameters':{'robot_description':xml}}}))
child=subprocess.Popen(['ros2','run','robot_state_publisher','robot_state_publisher',
                        '--ros-args','--params-file',str(params)],start_new_session=True)
try:
    end=time.monotonic()+15
    while not buffer.can_transform('base_link','lidar_link',Time()) and time.monotonic()<end:
        rclpy.spin_once(node,timeout_sec=0.05)
    tf=buffer.lookup_transform('base_link','lidar_link',Time()).transform
    actual=[tf.translation.x,tf.translation.y,tf.translation.z]
    print('Actual base_link -> lidar_link translation:',actual,flush=True)
    assert all(math.isclose(a,b,abs_tol=1e-9) for a,b in zip(actual,[args.x,0,args.z]))
    cmd=['timeout','10','ros2','run','tf2_ros','tf2_echo','base_link','lidar_link']
    print('$', ' '.join(cmd),flush=True)
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    print(result.stdout+result.stderr,flush=True)
    print('tf2_echo exit_code=',result.returncode,flush=True)
    assert result.returncode==124 and 'Translation:' in result.stdout
finally:
    if child.poll() is None:
        os.killpg(child.pid,signal.SIGINT)
    code=child.wait(timeout=15)
    print('RSP exit_code=',code,flush=True)
    node.destroy_node(); rclpy.try_shutdown()
    temporary.cleanup()
    assert code==0
