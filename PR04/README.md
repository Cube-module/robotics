# ПР04 — параметры движения patrol

Рабочая папка сдачи: `/home/a-god/robotics/PR04`. Пакеты скопированы из
завершённой ПР03 и доработаны здесь; каталоги PR01/PR02/PR03 не изменяются.
Среда: Ubuntu 24.04 в WSL2, ROS 2 Jazzy, ROS_DOMAIN_ID=47.
Команды Linux выполняются из Windows через `wsl.exe -d Ubuntu-24.04 -- bash -lc "..."`.

## Требования и реализация

Источник задания: https://ros.lms.ci.nsu.ru/practices/pr04
Текущий на момент подготовки комплект: `v1-w07`; неизменяемый URL и SHA закреплены в CI.

| Параметр | По умолчанию | Допустимо |
| --- | --- | --- |
| linear_speed | 0.5 м/с | конечное число от 0 до 1 |
| turn_rate | 0.3 рад/с | конечное число от −1 до 1 |
| publish_hz | 10.0 Гц | конечное число от 1 до 30 |

`control.select_parameters(current, updates)` возвращает проверенную копию,
не меняя входы. Строки, bool, NaN, бесконечности и значения вне диапазона
отклоняются. Целые и вещественные числа поддерживаются.

В существующей ноде сохранены подписка `/turtle1/pose`, поле `pose`,
относительный publisher `cmd_vel` и timer callback. До первой Pose команда
нулевая, после Pose используются активные скорости. Тип проверен в установленном
Jazzy: `turtlesim/msg/Pose`.

`validate_parameters` не имеет побочных эффектов. Только после принятия
всего атомарного набора параметров `apply_parameters` вычисляет новый период,
останавливает и уничтожает старый таймер и создаёт один новый. При отказе
сохраняются прежние параметры, тот же объект таймера и поток сообщений.
Изменение скоростей или повтор той же частоты не заменяет таймер.
Используется обычный однопоточный executor.

## Сборка и проверки

В новом Linux shell, из PR04:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=47
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest src/patrol/test
python3 -m pytest -q scripts/test_ros_support.py
(cd src/turtle_bringup && python3 -m pytest -q test)
colcon test --packages-select turtle_bringup patrol --event-handlers console_direct+
colcon test-result --verbose
QT_QPA_PLATFORM=offscreen python3 scripts/check_pr04.py
python3 .course-kit/v1/tools/check_practice.py PR04 --submission .
```

Для автоматического опыта домен должен быть свободен от других patrol/turtlesim.
Сценарий сам запускает и останавливает только свои процессы. Наблюдатель считает
реальные Twist, одновременно с ros2 param set/get проверяет исходные 10 Гц,
отказ для 0, −1, NaN, inf, 31, переход 10→5 Гц, сохранение 5 Гц после отказа,
изменение скоростей, вызов /clear и обнаружение action.
Проверяются и интервалы сообщений, и их число за измеренное время:
поток двух таймеров не должен пройти как правильная частота.
Допуск измерения ±20%, окно 4 секунды; значения не подменяются при отказе.
`--output path.json` сохраняет измерения только после успешных утверждений.

Два исходных шаблонных copyright-теста остаются пропущенными.
Flake8, pep257, функциональные тесты и регрессии DDS discovery выполняются.
Общий ROS helper и его regression-тесты перенесены из ПР03.

## Ручной повтор

В двух терминалах с одинаковым окружением:

```bash
ros2 launch turtle_bringup sim.launch.py
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В третьем:

```bash
ros2 topic type /turtle1/pose
ros2 param get /patrol publish_hz
ros2 param set /patrol publish_hz 0.0
ros2 param set /patrol publish_hz 5.0
ros2 param set /patrol linear_speed 0.8
ros2 param set /patrol turn_rate -0.6
ros2 topic hz /turtle1/cmd_vel
ros2 service call /clear std_srvs/srv/Empty '{}'
ros2 action list -t
```

ROS CLI может вернуть exit=0 даже при отказе параметра: сценарий обязательно
проверяет текст ответа, читает значение обратно и измеряет поток.
SIGINT для Jazzy ros2 run посылается всей отдельной группе, как терминальный Ctrl+C.

## Воспроизведение дефекта

Отдельная локальная ветка `pr04-defect` содержит намеренный обход проверки
только publish_hz. После её сборки и source тем же сценарием выполняется:

```bash
QT_QPA_PLATFORM=offscreen python3 scripts/check_pr04.py --expect-defect
```

Этот режим требует реального ZeroDivisionError в вычислении периода после
`ros2 param set /patrol publish_hz 0.0`, ненулевого кода завершения patrol
и исчезновения издателя. Он не является рабочим режимом patrol.
Исправленная ветка запускает тот же нулевой запрос и требует отказа с
сохранением 10 Гц, затем проверяет переход на 5 Гц.
Точный SHA дефекта и реальные логи находятся в evidence/pr04.

## Отчёт и CI

Commit A содержит реализацию, тесты, README и GitHub workflow.
Следующий commit B содержит только evidence/pr04 и AI_USAGE.md;
report.commit указывает SHA(A). Сдача — SHA(B) и успешный CI для B.
Workflow: `../.github/workflows/pr04.yml`; он собирает и тестирует пакеты,
выполняет настоящий headless ROS-опыт и неизменённый checker course-kit.
Удалённый CI можно подтвердить только после отдельного разрешения на push.
AI_USAGE.md сохраняет декларации предыдущих практик и добавляет PR04.

Для param get/set сценарий использует --no-daemon --spin-time 2 --timeout 8:
Jazzy ожидает появление ноды до 8 секунд, без кэша старого ROS daemon.
Общий лимит CLI-запроса остаётся ограниченным; ошибки не превращаются в успех.

Наблюдатель постоянно подключён к одному SingleThreadedExecutor; callbacks Pose
и Twist обрабатываются без переподключения ноды на каждом spin_once.
В измерениях сохраняются и времена приёма, и DDS source timestamps.
Отдельная регрессия проверяет поток 10 Гц одновременно с Pose около 62,5 Гц.
