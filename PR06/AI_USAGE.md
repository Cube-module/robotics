# Использование ИИ

- Использован ИИ: да, ChatGPT.
- Затронутые файлы: graph.md, environment.json, report.json и эта декларация.
- Помощь: объяснение команд ROS 2 и принципов работы ROS_DOMAIN_ID, подготовка команд для проведения эксперимента, сбор evidence, интерпретация результатов и оформление отчёта.
- Проверка: команды выполнены пользователем в локальном окружении WSL2 с ROS 2 Jazzy. Реальные stdout и коды завершения сохранены в evidence/pr01. Результаты не сгенерированы вместо запуска ROS. Поля report.json сверены с фактически полученными результатами; публичный checker запущен отдельно после оформления файлов.
- Время в report.json отражает фактическое время, затраченное на самостоятельное выполнение PR01.

Переписка, личные промпты и секреты не включены.

# AI Usage

AI tools were used to explain ROS 2 concepts, assist with commands, diagnose errors, and prepare the PR02 report and evidence.

# Декларация использования ИИ

## PR03

- Использован ИИ: да (ai_used: true).
- Модель: GPT-6, агент Codex; точный идентификатор сборки не предоставлен.
- Интерфейс: Codex на Windows, Linux-команды через wsl.exe, Ubuntu-24.04.
- Помощь: диагностика Git и исходников, выделение choose_command, завершение SIGINT,
  тесты и сценарии открытого эталона, адаптация к Jazzy, README, GitHub workflow, evidence.
- Источник проверок: https://gitverse.ru/virusapex/ros2-student/content/pr03
  commit a0ca1924c024038487fadad390c99131d1b73e27. Состояние в тесте адаптировано
  к существующему self.pose; исправлены замечания flake8 и доставка SIGINT в Jazzy.
- Проверка результата: реальные colcon build/test, pytest, turtlesim и CLI, официальный
  неизменённый course-kit. Сырой вывод сохранён в evidence/pr03.
- Отдельная ручная проверка владельцем и удалённый GitHub CI не заявляются.
- PR01/PR02 не изменялись. Созданы только разрешённые локальные коммиты; push не выполнялся.

## PR04

| Модель | Инструмент / среда | Компоненты | Характер помощи | Как проверено |
| --- | --- | --- | --- | --- |
| Codex (GPT-6; точный идентификатор сборки недоступен) | Windows Codex; Linux/ROS через wsl.exe в Ubuntu-24.04 | patrol, control, tests, checker script, evidence, GitHub CI | Параметры, валидация, замена таймера, defect experiment, диагностика discovery, отчёт | Реальные pytest, colcon, ROS runtime experiments и официальный course-kit checker |

Использован ИИ: да; ai_used: true. Декларации предыдущих практик выше сохранены.
Ручная проверка владельцем и удалённый GitHub Actions не заявляются; push не выполнялся.


## PR05

| Model | Tool / environment | Components | Assistance | Verification |
| --- | --- | --- | --- | --- |
| Codex | Windows agent; WSL2 Ubuntu-24.04, ROS 2 Jazzy | course_bringup, launch, QoS, bag configuration, tests, experiment script, documentation | Requirements analysis, implementation, test runs and corrections | Real colcon tests, live ROS QoS experiment, MCAP recording/replay; final evidence and course-kit result are recorded in PR05/evidence/pr05 |

AI was used: yes (ai_used: true). The earlier declarations above are retained.
Patrol was reused unchanged from PR04. No remote CI or owner manual review is claimed.
Local commits are authorized; no git push is performed.

PR05 final verification: colcon reported 58 tests, 0 errors, 0 failures, 1 inherited skip. The final live experiment reproduced the QoS defect (echo exit 124), verified the BEST_EFFORT fix, recorded 1127 MCAP messages and received replayed messages with the QoS override after the live source was stopped. Launch recording produced 246 messages. The unchanged official course-kit v1-w07 checker passed. Raw logs and metadata are preserved in PR05/evidence/pr05.


## PR06

| Model | Tool / environment | Components | Assistance | Verification |
| --- | --- | --- | --- | --- |
| Codex | Windows agent, WSL2 Ubuntu-24.04, ROS 2 Jazzy | course_description, Xacro, launch, RViz, model tests, TF/QoS scripts, CI and evidence | Analysis of the official assignment and original SDF, implementation, actual command execution and corrections | Independent SDF-based geometry tests, check_urdf, colcon, real TF/QoS experiments and RViz; final outcomes recorded in PR06/evidence/pr06 |

AI was used (ai_used: true). Previous declarations are preserved. The owner's
pre-existing uncommitted PR05 launch-file edit is preserved and excluded from PR06 commits.
The GitHub CI result is reported only after observing the actual remote run.
