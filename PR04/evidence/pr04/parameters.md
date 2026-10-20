# ПР04 — параметры и воспроизводимый дефект

Реализация: 7d8a645a6edba956961774f11496d6200a7befe6. Дефект: 73ebc151a5d40b4d3a9cd20b9a31cf9b99c2f2af (pr04-defect).
Среда и версии записаны в environment.json; весь опыт — реальные ROS процессы в WSL2.
Параметры по умолчанию: linear_speed=0.5, turn_rate=0.3, publish_hz=10.0.
Диапазоны конечных чисел: [0,1], [-1,1], [1,30] соответственно.

## Причина и исправление
В отдельном worktree отключена только проверка publish_hz (intentional-defect.patch).
После запроса publish_hz=0.0 post-set callback вычисляет 1.0/0.0: ZeroDivisionError,
код завершения patrol 1, издатель исчез. CLI не получает ответ и останавливается
по ограничению времени; это не доказательство само по себе — сохранён traceback ноды.
Сценарии обоих состояний побайтно одинаковы (defect-provenance.json).

В исправленной версии on-set callback валидирует весь набор без побочных эффектов.
Post-set callback вызывается только после принятия всех параметров и затем заменяет
таймер. Тесты проверяют сохранение именно прежнего объекта при отказе, единственный
живой таймер после принятия и отсутствие частичного применения ошибочного набора.

## Измерения исправленной ноды
| Этап | Сообщений | Длительность, с | Измерено, Гц |
| --- | ---: | ---: | ---: |
| Старт 10 Гц | 40 | 4.0153 | 10.0050 |
| После отклонения 0 при 10 Гц | 40 | 4.0002 | 9.9986 |
| После -1, NaN, inf и 31 | 40 | 4.0156 | 10.0008 |
| После принятия 5.0 | 20 | 4.0150 | 5.0002 |
| После отклонения 0 при 5 Гц | 20 | 4.0159 | 4.9974 |

Реальный Pose type: turtlesim/msg/Pose.
Runtime Twist после принятия скоростей: {"linear_x": 0.8, "angular_z": -0.6, "messages": 5}.

## Service и action — два предложения
Запрос service /clear предполагает один ответ на короткую операцию очистки.
Цель action /turtle1/rotate_absolute запускает длительную операцию, у которой есть feedback, результат и возможность отмены.

## Реальные команды и вывод — дефект
Из worktree pr04-defect после source /opt/ros/jazzy/setup.bash и install/setup.bash, ROS_DOMAIN_ID=47:
```text
$ QT_QPA_PLATFORM=offscreen python3 -u scripts/check_pr04.py --expect-defect --output /home/a-god/robotics/PR04/.course-kit/runs/defect-final.json
$ ros2 launch turtle_bringup sim.launch.py
$ ros2 topic type /turtle1/pose --no-daemon --spin-time 2 (attempt 1)
exit=0, stdout='turtlesim/msg/Pose\n', stderr=''
$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 10.0
$ ros2 param get /patrol linear_speed --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 0.5
$ ros2 param get /patrol turn_rate --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 0.3
MEASURE {"duration_s": 4.00005480599998, "messages": 39, "hz": 9.996549764507547, "count_hz": 9.749866412205401, "expected_hz": 10.0, "source_hz": 9.997405707420576}
$ ros2 param set /patrol publish_hz 0.0 --no-daemon --spin-time 2 --timeout 8
exit=2; timeout=True
PASS defect reproduced: publish_hz=0.0 raised ZeroDivisionError; patrol exited and its publisher disappeared
PROCESS LOG ['ros2', 'run', 'patrol', 'patrol', '--ros-args', '-r', 'cmd_vel:=/turtle1/cmd_vel']:
Traceback (most recent call last):
  File "/home/a-god/robotics/PR04/.course-kit/defect-worktree/PR04/install/patrol/lib/patrol/patrol", line 33, in <module>
    sys.exit(load_entry_point('patrol', 'console_scripts', 'patrol')())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/a-god/robotics/PR04/.course-kit/defect-worktree/PR04/build/patrol/patrol/patrol.py", line 90, in main
    rclpy.spin(node)
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/__init__.py", line 247, in spin
    executor.spin_once()
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 926, in spin_once
    self._spin_once_impl(timeout_sec)
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 918, in _spin_once_impl
    raise handler.exception()
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/task.py", line 286, in _execute_coroutine_step
    result = coro.send(None)
             ^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 592, in handler
    await call_coroutine()
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 531, in _execute
    response = await await_or_execute(srv.callback, request, srv.srv_type.Response())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/executors.py", line 115, in await_or_execute
    return callback(*args)
           ^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_service.py", line 117, in _set_parameters_callback
    result = node.set_parameters_atomically([param])
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 839, in set_parameters_atomically
    return self._set_parameters_atomically(parameter_list)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 859, in _set_parameters_atomically
    return self._set_parameters_atomically_common(parameter_list)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 962, in _set_parameters_atomically_common
    self._call_post_set_parameters_callback(parameter_list)
  File "/opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py", line 1055, in _call_post_set_parameters_callback
    callback(parameter_list)
  File "/home/a-god/robotics/PR04/.course-kit/defect-worktree/PR04/build/patrol/patrol/patrol.py", line 63, in apply_parameters
    period = 1.0 / candidate['publish_hz']
             ~~~~^~~~~~~~~~~~~~~~~~~~~~~~~
ZeroDivisionError: float division by zero
[ros2run]: Process exited with failure 1

PROCESS LOG ['ros2', 'launch', 'turtle_bringup', 'sim.launch.py']:
[INFO] [launch]: All log files can be found below /home/a-god/.ros/log/2026-10-20-22-51-19-673725-GOD-2612
[INFO] [launch]: Default logging verbosity is set to INFO
[INFO] [turtlesim_node-1]: process started with pid [2615]
[turtlesim_node-1] [INFO] [1792511479.761405753] [turtlesim]: Starting turtlesim with node name /turtlesim
[turtlesim_node-1] [INFO] [1792511479.766401039] [turtlesim]: Spawning turtle [turtle1] at x=[5.544445], y=[5.544445], theta=[0.000000]
[WARNING] [launch]: user interrupted with ctrl-c (SIGINT)
[INFO] [turtlesim_node-1]: sending signal 'SIGINT' to process[turtlesim_node-1]
[turtlesim_node-1] [INFO] [1792511513.128953696] [rclcpp]: signal_handler(SIGINT/SIGTERM)
[INFO] [turtlesim_node-1]: process has finished cleanly [pid 2615]
```

## Реальные команды и вывод — исправленная версия
```text
$ QT_QPA_PLATFORM=offscreen python3 -u scripts/check_pr04.py --output evidence/pr04/runtime.json
$ ros2 launch turtle_bringup sim.launch.py
$ ros2 topic type /turtle1/pose --no-daemon --spin-time 2 (attempt 1)
exit=0, stdout='turtlesim/msg/Pose\n', stderr=''
$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 10.0
$ ros2 param get /patrol linear_speed --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 0.5
$ ros2 param get /patrol turn_rate --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 0.3
MEASURE {"duration_s": 4.015318779000154, "messages": 40, "hz": 10.005023024374804, "count_hz": 9.961849158576724, "expected_hz": 10.0, "source_hz": 10.000710930025736}
$ ros2 param set /patrol publish_hz 0.0 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: publish_hz must be finite and in [1.0, 30.0]

$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 10.0
MEASURE {"duration_s": 4.000183511000159, "messages": 40, "hz": 9.998592710894927, "count_hz": 9.999541243546316, "expected_hz": 10.0, "source_hz": 9.997541081699707}
$ ros2 param set /patrol publish_hz -1.0 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: publish_hz must be finite and in [1.0, 30.0]

$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 10.0
$ ros2 param set /patrol publish_hz .nan --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: publish_hz must be finite and in [1.0, 30.0]

$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 10.0
$ ros2 param set /patrol publish_hz .inf --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: publish_hz must be finite and in [1.0, 30.0]

$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 10.0
$ ros2 param set /patrol publish_hz 31.0 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: publish_hz must be finite and in [1.0, 30.0]

$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 10.0
MEASURE {"duration_s": 4.015565148000178, "messages": 40, "hz": 10.000824183306653, "count_hz": 9.961237964205537, "expected_hz": 10.0, "source_hz": 10.00108823379701}
$ ros2 param set /patrol publish_hz 5.0 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Set parameter successful
$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 5.0
MEASURE {"duration_s": 4.015039553999941, "messages": 20, "hz": 5.000164527781998, "count_hz": 4.981270976539997, "expected_hz": 5.0, "source_hz": 4.99945546325788}
$ ros2 param set /patrol publish_hz 0.0 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: publish_hz must be finite and in [1.0, 30.0]

$ ros2 param get /patrol publish_hz --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 5.0
MEASURE {"duration_s": 4.015880376999803, "messages": 20, "hz": 4.997407397646147, "count_hz": 4.980228025353102, "expected_hz": 5.0, "source_hz": 4.998661829288678}
$ ros2 param set /patrol linear_speed 0.8 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Set parameter successful
$ ros2 param set /patrol turn_rate -0.6 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Set parameter successful
$ ros2 param set /patrol linear_speed 1.1 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: linear_speed must be finite and in [0.0, 1.0]

$ ros2 param set /patrol turn_rate -1.1 --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
stderr:
Setting parameter failed: turn_rate must be finite and in [-1.0, 1.0]

$ ros2 param get /patrol linear_speed --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: 0.8
$ ros2 param get /patrol turn_rate --no-daemon --spin-time 2 --timeout 8
exit=0; timeout=False
Double value is: -0.6
$ ros2 service call /clear std_srvs/srv/Empty {}
exit=0; timeout=False
waiting for service to become available...
requester: making request: std_srvs.srv.Empty_Request()

response:
std_srvs.srv.Empty_Response()

$ ros2 action list -t
exit=0; timeout=False
/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]
PASS PR04 runtime: rejected values preserve flow; 10 -> 5 Hz; runtime speeds, /clear, action discovery and shutdown
```

Полный вывод процессов сохранён в runtime.txt. Ответ CLI об отказе проверяется явно:
exit=0 сам по себе не означает принятие параметра.
Первый пробный замер оказался ниже допуска; другой пробный прогон выявил Node not found.
Оба неуспешных прогона не используются как доказательство PASS. Для param get/set
добавлено штатное ограниченное ожидание Jazzy --no-daemon --spin-time 2 --timeout 8.
Наблюдатель закреплён за SingleThreadedExecutor; добавлена регрессия одновременного
приёма частых Pose и Twist и сохранены DDS source timestamps для диагностики.
Финальные результаты выше получены новым запуском проверенного сценария.
В сыром логе могут быть предупреждения turtlesim о стене: контроль маршрута не входит
в эту практику; измеряются реальные команды и параметры, а не следование маршруту.

Удалённый GitHub Actions и ручная проверка владельцем не заявляются. Push не выполнялся.
