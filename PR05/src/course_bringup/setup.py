from glob import glob

from setuptools import find_packages, setup

package_name = 'course_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='a-god',
    maintainer_email='arturbakirov1730@gmail.com',
    description='PR05 namespaced patrol, QoS demonstration and MCAP recording',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={'console_scripts': [
        'pose_relay = course_bringup.pose_relay:main',
        'pose_subscriber = course_bringup.pose_subscriber:main',
    ]},
)
