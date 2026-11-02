# Политика официального upstream Telegram

Перед подготовкой IPA NagramiX проверяет ветку по умолчанию официального Telegram-iOS:

| Платформа | Официальный репозиторий | Источник версии | Локальный pin |
| --- | --- | --- | --- |
| iOS | `TelegramMessenger/Telegram-iOS` | `versions.json` | `ios/upstream.env` |

`python3 scripts/check_upstreams.py` сообщает, актуален ли закреплённый commit. Параметр `--require-current` завершает проверку ошибкой при устаревшем pin. Обновление pin требует проверки метаданных версии и всех точных overlay-якорей, компиляции на macOS и регрессионного тестирования на физическом iPhone.
