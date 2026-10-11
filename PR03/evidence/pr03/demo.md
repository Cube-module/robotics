# ПР03: реальный опыт ROS 2 Jazzy

Реализация: 32ee127224a39bc03a5b344ef7616e07bd489ba0. Среда: WSL2 Ubuntu 24.04, ROS_DOMAIN_ID=16.
Опыт выполнен командой `QT_QPA_PLATFORM=offscreen python3 scripts/check_pr03.py`.
Полный вывод находится в live.txt и tests.txt.

Подписка /turtle1/pose сохраняет последнее сообщение в self.pose. Таймер 0,1 с
публикует Twist: до Pose нулевой, после Pose linear.x=0.5, angular.z=0.3.
Остальные компоненты нулевые. Чистая функция не изменяет входную позу.

Без remap (`ros2 run patrol patrol`) у /cmd_vel один publisher и ноль
subscribers; у /turtle1/cmd_vel ноль publishers и один subscriber turtlesim.
Совпадение типа сообщений не соединяет разные имена топиков.
Изменён только runtime remap:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

После remap CLI подтвердил один publisher и один subscriber. Затем наблюдатель
и ros2 topic hz добавили подписки для измерения. Проверены реальные Pose и Twist.

```text
PASS no Pose: five zero Twist messages
PASS defect: before=[5.544444561004639, 5.544444561004639, 0.0]; after=[5.544444561004639, 5.544444561004639, 0.0]; pose unchanged
PASS fix: 10.007s, 100 messages, 10.000 Hz, Twist=(0.5, 0.3)
PASS motion: before=[5.544444561004639, 5.544444561004639, 0.0]; after=[4.18670654296875, 6.238905906677246, -0.9503852725028992]
PASS SIGINT: patrol exited 0; no command publisher; watchdog stopped turtle at [4.589513301849365, 5.842344760894775, -0.6095852851867676]
PASS PR03 live experiment
```

SIGINT для ros2 run отправлен группе процессов, как терминальный Ctrl+C:
в установленном Jazzy ros2run.api.run_executable сам его не пересылает.
Для ros2 launch сигнал получает родитель, который завершает turtlesim.
После остановки patrol издатель исчезает и watchdog turtlesim останавливает движение.

Pytest: 11 passed/1 skipped для patrol и сценария; bringup: 2 passed/1 skipped.
Пропущены только два исходных шаблонных copyright-теста; flake8 и pep257 прошли.
Предупреждения Python 3.12 о fork из многопоточного flake8 сохранены в сыром логе.
Удалённый GitHub Actions не запускался: push не выполнялся.
