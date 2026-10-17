# NagramiX 0.5.9: сборка и релиз готовы

17октября опубликован полноценный [GitHub Release0.5.9](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.9), build97: не черновик и не prerelease. [IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.9/NagramiX-0.5.9-unsigned.ipa) требует внешней подписи для физического iPhone, минимум iOS15.0.

- [Нативная сборка](https://github.com/Mr-EFES/NagramiX/actions/runs/39028343221): success, release_arm64, macOS/Xcode/Bazel.
- Исходный коммит приложения и тегv0.5.9: `3ff65e9b7d72f4d78a105df47f734df73b9e3248`.
- База Telegram13.0: `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`.
- Размер IPA: 88526724байт; SHA-256: `41b812d937f63a1ee5b389a90eafd98db46082d3a9c5cffbd1b541463abad1ee`.
- Независимая проверка опубликованного файла: ZIP CRC, версия0.5.9/build97, provenance/checksum, отсутствие подписей/профилей, все6бинарных файлов ARM64, iOS15.0, фоновое аудио,8иконок,7приветственных PNG,31мелодия, RU292/EN218 значений локализации.

Включены [фоновые транзакции](BACKGROUND_TRANSACTION_LIFETIME.md), [жизненный цикл камеры](CAMERA_PREVIEW_WATCHDOG_FIX.md), [завершение кружка](ROUND_VIDEO_COLD_FINALIZATION.md), [исключения уведомлений](NOTIFICATION_EXCEPTION_PICKER_FIX.md), [история правок](../product/features/edit-history.md), [эмодзи закреплений](PINNED_PREVIEW_EMOJI_FIX.md), подписи профиля и перевод debug UI. [Полный changelog/функции](../product/releases/0.5.9.md).

Физическая приёмка ожидается по [плану](IPHONE_TEST_0.5.9.md). Четыре нативных XCTest камеры подготовлены, но не исполнялись. Компиляция не доказывает отсутствие всех будущих вылетов; конкретная транзакция/файл из stripped-отчётов94 не установлены.

Прежние релизы и IPA сохранены. Попытки95/96 отменены до публикации, версия осталась0.5.9. После этой готовой сборки следующий рабочий выпуск0.5.10 требует новой команды. Документальный checkpoint после публикации не меняет исходный коммит приложения или тег и не запускает новую сборку.
