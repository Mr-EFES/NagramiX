# Подготовка NagramiX

NagramiX — overlay-репозиторий iPhone-клиента на закреплённых официальных исходниках Telegram-iOS. Полное дерево upstream здесь не хранится.

## Подготовка

1. Проверить pin командой `python3 scripts/check_upstreams.py --platform ios --require-current`.
2. Получить `TELEGRAM_IOS_REF` из `ios/upstream.env` во временный каталог.
3. Применить `python3 ios/apply_overlay.py --source <checkout> --configuration <temporary configuration.json>`.
4. Проверить сгенерированные изменения и выполнить статические проверки.

Нельзя коммитить checkout upstream, временные конфигурации и профили, результаты сборки или материалы подписи.

## Авторитетная сборка

`.github/workflows/build-unsigned-ipa.yml` запускается на macOS, применяет overlay, компилирует ARM64 и упаковывает неподписанный IPA. `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` хранятся только в GitHub Secrets. Проверка на физическом iPhone выполняется отдельно от компиляции.
