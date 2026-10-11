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
