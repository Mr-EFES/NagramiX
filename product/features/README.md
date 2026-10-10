# Жизненный цикл функций

Все реализованные функции текущего реестра включены в чистую нативную сборку №83 и новый проверенный IPA NagramiX 0.5.1 на Telegram13.0: compile_passed/device_pending. Включены [звуки](../../docs/NOTIFICATION_SOUNDS_FIX.md), [яркость QR](../../docs/PROXY_QR_BRIGHTNESS_FIX.md), [истории инкогнито](story-incognito.md), [два режима ускорения](download-acceleration.md) и [раздельные кнопки](../../docs/PROFILE_NAVIGATION_LAYOUT_FIX.md). Компиляция не заменяет испытания на устройстве. [Отчёт](../../docs/RELEASE_STATUS.md), [план iPhone](../../docs/IPHONE_TEST_0.5.1.md).

Выпуск включает [сохранённые кружки](../../docs/ARCHIVED_ROUND_VIDEO_FIX.md), [полные фотографии](../../docs/PHOTO_JPEG_COMPATIBILITY_FIX.md), [меню и просмотр по аватарке](chat-actions-on-hold.md), [пересылку и рассылку](message-distribution.md), [фоновое видео](video-playback-options.md), [панель канала](channel-bottom-panel.md), [двойной тап и реакции](message-interaction-options.md), [ускорение скачивания](download-acceleration.md). Скорость скачивания и поведение на устройстве ещё не измерены.

`registry.json` описывает реализацию и отдельные уровни проверки. Поле release содержит текущую версию; при новых изменениях compile_pending означает необходимость новой нативной сборки.

| Поле | Статус | Значение |
| --- | --- | --- |
| `specification` | `specified` | Поведение описано. |
| `ios.implementation` | `implemented` | Реализация включена в overlay. |
| `ios.compile` | `compile_passed` / `compile_pending` | Нативная компиляция подтверждена / изменённые исходники ожидают следующей сборки. |
| `ios.device` | `device_pending` | Нужна проверка на физическом устройстве. |
| `ios.device` | `device_passed` | Проверка на устройстве подтверждена. |

Реализация, компиляция и проверка устройства — отдельные критерии. Статус одного критерия не заменяет остальные. Для защищённых функций правила `AGENTS.md` обязательны независимо от полноты реестра; уточнять записи по фактическим результатам проверок.

Перед публикацией изменения версии выполнить `python3 scripts/validate_release_metadata.py`. Аннотация текущего релиза находится в `product/releases/` и синхронизируется с GitHub Releases.
