# ПР03. Первая нода: поза и команда

Ветка `pr03` продолжает `pr02`: пакет `turtle_bringup` сохранён, рядом добавлен
`patrol`. Ветки `pr01`, `pr02` и `main` содержат прежние работы.
Рабочая папка этой практики: `/home/a-god/robotics/PR03`.
ПР01/ПР02 сохранены в соседних каталогах и не изменяются. Здесь CI проверяет ПР03. Пример выполняет обязательную часть без маршрута мышью.

## Что читать

- [Нода](src/patrol/patrol/patrol.py) — подписка, состояние и таймер.
- [Чистая функция](src/patrol/patrol/control.py) и [тесты](src/patrol/test/test_patrol.py).
- [Опыт, команды и объяснение](evidence/pr03/demo.md), [сырой вывод проверок](evidence/pr03/tests.txt), [отчёт](evidence/pr03/report.json).
- [CI](../.github/workflows/pr03.yml), [помощь ИИ](AI_USAGE.md).

## Сборка и показ

Среда: WSL2, Ubuntu 24.04, ROS 2 Jazzy. Все команды ниже выполняются в PR03.
В каждом терминале подключите ROS, выберите свой домен (в этом примере 16)
и подключите workspace. Не запускайте одновременно старый patrol или teleop.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest -q src/patrol/test scripts/test_check_pr03.py
```

В терминале A: `ros2 launch turtle_bringup sim.launch.py`.
В B: `ros2 run patrol patrol`. В C:

```bash
ros2 node info /patrol
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
```

У `/cmd_vel` один издатель и нет подписчиков: черепаха не движется.
Остановите B и измените только remap:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В C: `ros2 topic hz /turtle1/cmd_vel`; измеряйте 10 секунд и остановите
измеритель Ctrl+C. Затем остановите B: после watchdog turtlesim движение
прекратится. Закройте A. Программа до первой Pose публикует нулевой Twist,
после — `(linear.x=0.5, angular.z=0.3)`. Контроль возраста Pose здесь не реализован.

## Автоматическое повторение

После сборки и source в том же терминале:

```bash
QT_QPA_PLATFORM=offscreen python3 scripts/check_pr03.py
```

Это настоящий ROS-опыт без видимого окна: проверяет нулевую команду до Pose,
разрыв имени, исправление только remap, частоту за 10 секунд, движение и
завершение по SIGINT. Наблюдатель временно подписывается на правильный cmd_vel,
поэтому во время измерения подписчиков больше, чем при ручном опыте.
Каждый диагностический CLI-запрос ждёт нужный тип и количество endpoints
не более 20 секунд: новый участник DDS может ещё не видеть работающие ноды.
Повторяются только отсутствие объекта и неполный граф; остальные ошибки CLI
сразу прерывают проверку. В логе видны номер попытки, код возврата и оба потока.
Никакие файлы в evidence скрипт сам не переписывает: результат выводится в stdout.

Чистые тесты и ROS-тесты запускаются явным pytest, чтобы успешный `colcon test`
без обнаруженных тестов не считался доказательством. GitHub Actions выполняет сборку, тесты, этот сценарий и официальный checker.
Удалённый запуск появится только после разрешённого владельцем push.

## Проверка отчёта комплектом курса

```bash
curl -fsSLo course-kit.tar.gz \
  https://ros.lms.ci.nsu.ru/downloads/robotics-course-kit-v1-w03-7fbfd3e8161a.tar.gz
printf '%s  %s\n' \
  7fbfd3e8161ab6c6ebefc7663efdaf77d9a7d490399743507f33dcefbd5ac522 \
  course-kit.tar.gz | sha256sum -c -
mkdir -p .course-kit/pr03
tar -xzf course-kit.tar.gz -C .course-kit/pr03
python3 .course-kit/pr03/v1/tools/check_practice.py PR03 --submission .
```

Проверка отчёта дополняет тесты, но не доказывает работу ноды сама по себе.
Комплект, build/install/log и временные кэши не входят в Git.

## Отчёт и история

Сначала фиксируются код, тесты, README и workflow (коммит A). Затем реальные
результаты, report.json с SHA коммита A и запись PR03 в AI_USAGE.md (коммит B).
Сдаётся B со ссылкой на его CI. Локальный прогон не заменяет удалённый run:
push в GitHub требует отдельного разрешения владельца.

Предыдущая ПР02 описана в `../PR02/evidence/pr02/commands.md`.

Проверочные сценарии взяты из открытого эталона преподавателя:
https://gitverse.ru/virusapex/ros2-student/content/pr03
(коммит `a0ca1924c024038487fadad390c99131d1b73e27`).
Тест состояния использует существующее имя поля `pose`; поведенческие проверки сохранены.
Унаследованные тесты copyright пока пропускаются; flake8 и pep257 выполняются.

В Jazzy проверка отправляет SIGINT группе процессов `ros2 run`, как Ctrl+C
в терминале; `ros2 launch` сам пересылает сигнал дочерней ноде.
