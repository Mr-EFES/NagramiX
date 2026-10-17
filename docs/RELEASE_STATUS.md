# NagramiX 0.5.9: подготовка сборки и публикации

17октября пользователь разрешил исправить русский перевод отладки Telegram13.0, собрать все накопленные правки для физического iPhone и опубликовать полноценный GitHub Release0.5.9 с changelog. Используется отдельный checkout от main, прежний root WIP/staged rename и готовые релизы сохраняются.

Включены все исправления после0.5.8/build94: [watchdog камеры](CAMERA_PREVIEW_WATCHDOG_FIX.md), [отправка/preview кружков](ROUND_VIDEO_COLD_FINALIZATION.md), [исключения уведомлений](NOTIFICATION_EXCEPTION_PICKER_FIX.md), [история правок](../product/features/edit-history.md), [эмодзи закреплений](PINNED_PREVIEW_EMOJI_FIX.md), подписи профиля и завершение русского debug UI. Добавлено19ключей RU/EN и4форматируемых сообщения, сохранены диагностические значения и действия.

[Changelog и функции](../product/releases/0.5.9.md) · [Приёмка на iPhone](IPHONE_TEST_0.5.9.md).

Нативная компиляция новых правок, исполнение XCTest и физическая приёмка пока не подтверждены. Источник/номер run/build, checksum и результат упаковки будут записаны после сборки. Последний готовый IPA0.5.8/build94 и его GitHub Release сохранены.
