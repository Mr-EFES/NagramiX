# Подготовка NagramiX

NagramiX — overlay-репозиторий iPhone-клиента на закреплённых официальных исходниках Telegram-iOS. Полное дерево upstream здесь не хранится.

## Подготовка

1. Проверить pin командой `python3 scripts/check_upstreams.py --platform ios --require-current`.
2. Получить `TELEGRAM_IOS_REF` из `ios/upstream.env` во временный каталог.
3. Применить `python3 ios/apply_overlay.py --source <checkout> --configuration <temporary configuration.json>`.
4. Проверить сгенерированные изменения и выполнить статические проверки.

Нельзя коммитить checkout upstream, временные конфигурации и профили, результаты сборки или материалы подписи.

## Доступ к GitHub без интерактивных подтверждений

Для автоматизированной работы `origin` должен указывать на
`https://github.com/Mr-EFES/NagramiX.git`, а GitHub CLI должен получать учётные
данные из защищённой переменной окружения `GH_TOKEN`. Такой способ не открывает
браузер и не требует подтверждать короткоживущий device code во время каждой
сессии.

1. Создать для автоматизации отдельный fine-grained personal access token с
   доступом только к репозиторию `Mr-EFES/NagramiX`. Выдать лишь необходимые
   права: `Contents: Read and write`, `Pull requests: Read and write` и, только
   если нужно запускать или администрировать workflow, `Actions: Read and write`.
2. Сохранить токен в защищённом хранилище среды выполнения и передавать его как
   `GH_TOKEN`. Не вставлять токен в чат, команды, URL remote, файлы проекта или
   Git-конфигурацию.
3. Один раз настроить remote, если он отсутствует:

   ```bash
   git remote add origin https://github.com/Mr-EFES/NagramiX.git
   ```

4. Проверить неинтерактивный доступ:

   ```bash
   gh auth status
   gh api repos/Mr-EFES/NagramiX --jq '.full_name'
   git fetch origin --prune
   ```

Переменная `GH_TOKEN` имеет приоритет для GitHub CLI, поэтому отдельный
`gh auth login` в автоматизированной сессии не требуется. Для локального
компьютера человека допустим обычный `gh auth login`, но его учётные данные не
переносятся в новые изолированные среды автоматически.

## Авторитетная сборка

`.github/workflows/build-unsigned-ipa.yml` запускается на macOS, применяет overlay, компилирует ARM64 и упаковывает неподписанный IPA. `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` хранятся только в GitHub Secrets. Проверка на физическом iPhone выполняется отдельно от компиляции.
