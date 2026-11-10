"""Independent geometry/structure oracle from the original course SDF."""
import hashlib
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import xacro
import yaml

PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / 'reference/model.sdf'
SDF = ET.parse(SOURCE).getroot().find('model')
SENSORS = ('camera_link', 'lidar_link', 'imu_link')
WHEELS = ('front_left_wheel', 'front_right_wheel', 'rear_left_wheel', 'rear_right_wheel')
LINKS = {link.get('name') for link in SDF.findall('link')}


def expand(**kwargs):
    text = xacro.process_file(str(PACKAGE / 'urdf/vehicle.urdf.xacro'),
                              mappings={k: str(v) for k, v in kwargs.items()}).toxml()
    return ET.fromstring(text)


@pytest.fixture(scope='module')
def robot():
    return expand()


def vec(text):
    return np.array([float(x) for x in text.split()])


def transform(xyz, rpy):
    r, p, y = rpy
    cr, cp, cy = np.cos([r, p, y]); sr, sp, sy = np.sin([r, p, y])
    result = np.eye(4)
    result[:3, :3] = [[cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
                     [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr], [-sp, cp*sr, cp*cr]]
    result[:3, 3] = xyz
    return result


def origin(el):
    if el is None:
        return np.eye(4)
    return transform(vec(el.get('xyz', '0 0 0')), vec(el.get('rpy', '0 0 0')))


def absolute(robot, child):
    if child == 'base_link':
        return np.eye(4)
    joint = next(j for j in robot.findall('joint') if j.find('child').get('link') == child)
    return absolute(robot, joint.find('parent').get('link')) @ origin(joint.find('origin'))


def source_pose(name):
    values = vec(SDF.findtext("link[@name='" + name + "']/pose", '0 0 0 0 0 0'))
    return transform(values[:3], values[3:])


def test_source_checksum_and_dimensions():
    dimensions = yaml.safe_load((PACKAGE / 'config/dimensions.yaml').read_text())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == dimensions['source_sha256']
    assert dimensions['wheelbase'] == pytest.approx(source_pose(WHEELS[0])[0, 3] - source_pose(WHEELS[2])[0, 3])
    assert dimensions['track'] == pytest.approx(source_pose(WHEELS[0])[1, 3] - source_pose(WHEELS[1])[1, 3])


def test_urdf_parser(robot, tmp_path):
    filename = tmp_path / 'vehicle.urdf'
    filename.write_bytes(ET.tostring(robot))
    check = subprocess.run(['check_urdf', str(filename)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    assert 'root Link: base_link' in check.stdout
    assert 'gazebo' not in ET.tostring(robot, encoding='unicode')


def test_tree_is_complete_acyclic_and_has_one_parent(robot):
    assert {link.get('name') for link in robot.findall('link')} == LINKS
    parents = {}
    for joint in robot.findall('joint'):
        parent, child = joint.find('parent').get('link'), joint.find('child').get('link')
        assert child not in parents
        assert parent in LINKS and child in LINKS
        parents[child] = parent
    assert LINKS - parents.keys() == {'base_link'}
    for child in parents:
        seen = set()
        while child in parents:
            assert child not in seen
            seen.add(child)
            child = parents[child]
        assert child == 'base_link'


def test_lidar_parent_and_absolute_pose(robot):
    joint = robot.find("joint[@name='lidar_joint']")
    assert joint.find('parent').get('link') == 'base_link', 'lidar must be attached directly to base_link'
    np.testing.assert_allclose(absolute(robot, 'lidar_link'), source_pose('lidar_link'), atol=1e-9)


@pytest.mark.parametrize('name', SENSORS)
def test_sensor_transform_and_parent_match_sdf(robot, name):
    joint = next(j for j in robot.findall('joint') if j.find('child').get('link') == name)
    source_joint = next(j for j in SDF.findall('joint') if j.findtext('child') == name)
    assert joint.get('type') == 'fixed'
    assert joint.find('parent').get('link') == source_joint.findtext('parent')
    np.testing.assert_allclose(absolute(robot, name), source_pose(name), atol=1e-9)


def test_chassis_visual_collision_and_com_match_source(robot):
    body = robot.find("link[@name='base_link']")
    reference = SDF.find("link[@name='base_link']/visual")
    dimensions = vec(reference.findtext('geometry/box/size'))
    expected_origin = transform(vec(reference.findtext('pose'))[:3], [0, 0, 0])
    for kind in ('visual', 'collision'):
        np.testing.assert_allclose(vec(body.find(kind+'/geometry/box').get('size')), dimensions)
        np.testing.assert_allclose(origin(body.find(kind+'/origin')), expected_origin)
    np.testing.assert_allclose(origin(body.find('inertial/origin')), expected_origin)


@pytest.mark.parametrize('name', WHEELS)
def test_wheel_geometry_and_rolling_axis_match_sdf(robot, name):
    link = robot.find("link[@name='"+name+"']")
    src = SDF.find("link[@name='"+name+"']/visual/geometry/cylinder")
    for kind in ('visual', 'collision'):
        cylinder = link.find(kind+'/geometry/cylinder')
        assert float(cylinder.get('radius')) == float(src.findtext('radius'))
        assert float(cylinder.get('length')) == float(src.findtext('length'))
        np.testing.assert_allclose(absolute(robot, name) @ origin(link.find(kind+'/origin')),
                                   source_pose(name), atol=1e-6)
    joint = robot.find("joint[@name='"+name+"_joint']")
    assert joint.get('type') == 'continuous'
    np.testing.assert_allclose(vec(joint.find('axis').get('xyz')), [0, 1, 0])


@pytest.mark.parametrize('side', ['left', 'right'])
def test_steering_structure_and_limits(robot, side):
    name = 'front_'+side+'_steering_joint'
    joint = robot.find("joint[@name='"+name+"']")
    source = SDF.find("joint[@name='"+name+"']")
    assert joint.get('type') == 'revolute'
    assert joint.find('parent').get('link') == source.findtext('parent')
    assert joint.find('child').get('link') == source.findtext('child')
    np.testing.assert_allclose(vec(joint.find('axis').get('xyz')), [0, 0, 1])
    for key in ('lower', 'upper', 'effort'):
        assert float(joint.find('limit').get(key)) == float(source.findtext('axis/limit/'+key))
    assert float(joint.find('limit').get('velocity')) > 0


@pytest.mark.parametrize('wb,tr,radius', [(1.2, 0.62, 0.12), (0.8, 0.8, 0.12),
                                          (0.8, 0.62, 0.16), (1.2, 0.8, 0.16)])
def test_geometry_parameters_propagate(wb, tr, radius):
    robot = expand(wheelbase=wb, track=tr, wheel_radius=radius)
    for name in WHEELS:
        x = wb/2 if name.startswith('front') else -wb/2
        y = tr/2 if 'left' in name else -tr/2
        np.testing.assert_allclose(absolute(robot, name)[:3, 3], [x, y, 0])
        link = robot.find("link[@name='"+name+"']")
        for kind in ('visual', 'collision'):
            assert float(link.find(kind+'/geometry/cylinder').get('radius')) == radius
        mass = float(link.find('inertial/mass').get('value'))
        assert float(link.find('inertial/inertia').get('iyy')) == pytest.approx(mass*radius**2/2)
    for name in SENSORS:
        np.testing.assert_allclose(absolute(robot, name), source_pose(name))


@pytest.mark.parametrize('name', sorted(LINKS))
def test_positive_mass_and_physically_possible_inertia(robot, name):
    el = robot.find("link[@name='"+name+"']/inertial")
    mass = float(el.find('mass').get('value'))
    expected_mass = float(SDF.findtext("link[@name='"+name+"']/inertial/mass"))
    assert np.isfinite(mass) and mass > 0
    assert mass == pytest.approx(expected_mass)
    i = el.find('inertia').attrib
    tensor = np.array([[float(i['ixx']), float(i['ixy']), float(i['ixz'])],
                       [float(i['ixy']), float(i['iyy']), float(i['iyz'])],
                       [float(i['ixz']), float(i['iyz']), float(i['izz'])]])
    assert np.all(np.isfinite(tensor))
    principal = np.linalg.eigvalsh(tensor)
    assert np.all(principal > 0)
    assert 2*max(principal) <= sum(principal)+1e-12
