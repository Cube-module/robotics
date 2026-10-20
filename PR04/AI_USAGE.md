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
