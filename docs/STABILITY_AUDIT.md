# Аудит стабильности — 13 октября 2026

Проверены собственные исходники NagramiX, критические интеграции `ios/apply_features.py` и соответствующие участки закреплённого Telegram13.0. Исправлены три конкретные причины ошибок. Изменения только в рабочем дереве; опубликованный IPA0.5.3/build86 их не содержит. Статус: **implemented / compile_pending / device_pending**.

## Исправления

| Проблема | Последствие | Исправление |
| --- | --- | --- |
| Архивные Save Sound/Save Video вызывали `NagramiXArchivedMediaCopy.file`, объявленный `private` в другом файле | Ошибка доступности при Swift typecheck следующей сборки | Оба действия используют существующий `public prepare` с проверкой типа. Приватный метод/API helper не расширены |
| VideoRecorder бесконечно ожидал `isReadyForMoreMediaData` аудио/видео | Ошибка AVAssetWriter или постоянный backpressure занимают очередь; stop/cancel и таймер на той же очереди не выполняются | Проверка writer.status/error, ожидание не дольше2секунд на монотонных часах. При сбое очищаются pending audio buffers и отменяется writer. Отклонённый video append также переводит запись в ошибку |
| Original Video ставил асинхронный `MediaBox.moveResourceData` с Photos temp URL и сразу освобождал его через `EngineTempBox.dispose` | Очистка удаляет исходник раньше queued move: кэш не получает видео | Синхронный независимый upload pin через hardlink либо copy; queued MediaBox move забирает этот путь. Photos temp очищается отдельно. Большое fallback copy не удерживает cancellation lock; отменённый pin удаляется до передачи move. LocalFileMediaResource/метаданные/bytes/uploader прежние |

Рекордер изменяется поздним `apply_recorder_backpressure_fix`: полный SHA256 входа после предыдущих правок и четыре уникальные замены до записи. Guards и порядок остальных интеграций сохранены. Готовый writer проходит сразу; при медленном/перегруженном устройстве нужно проверить предел2секунды. Неисправная запись возвращает штатную ошибку, не объявляется успешно отправленной.

## Охват

- Архив: capture/restore/clear, ticket/transfer identity, полные файлы, локальное отображение, одиночная пересылка/рассылка, явно запрошенное сохранение.
- Медиа: original video cancellation/cleanup, метаданные/fast-start, JPEG/HD, lifecycle рекордеров/аудиосессия, voice/round end и одноразовый экран.
- Сеть: DNS/DoH parsing/cancellation, VPN policy, failover generations, bounded probes, ручной выбор и preferences.
- Интерфейс: настройки/поиск/проценты/категории, row identity/observers/disposables, readonly/deferred reactions, unread sorting, профильные ссылки, onboarding и оценка звонка.
- Интеграция: весь overlay на чистом sparse fixture закреплённого source, dependencies/resources, package/metadata checks и защищённые stock-палитры.

В остальных перечисленных участках дополнительные причины краша/зависания, достаточные для безопасной точечной правки, этой проверкой не подтверждены. Это не доказывает безошибочность и не является построчным аудитом всего многомиллионного upstream и внешних библиотек.

## Проверка

Native `MediaBox.swift` подтверждает `dataQueue.async`, `TempBox.swift` — независимую очередь удаления. Порядок «удаление раньше переноса» воспроизведён на настоящей ФС. Fetch/PendingMessageUploadedContent проверены для штатного транспорта; дополнительно скачанные файлы сверены с Git blob SHA закреплённого дерева.

Чистый proof `/tmp/nagramix-stability-audit-final-checked-proof` относительно `/tmp/nagramix-053-call-rating-checked-proof`: **453файла,449побайтно прежних, ровно4изменённых**, без новых/удалённых native файлов. Только LegacyMediaPickers, VideoRecorder и два новых archive-save helper. Storage/player/read/auth/proxy/settings/call/onboarding тела побайтно прежние.

`scripts/validate_stability_overlay.py`: четыре точные границы,4reverse для рекордера, drift/rerun отказ до записи, реальные hardlink/copy + queued move при ранней очистке — PASS. Это проверка интеграции/владения файлами, не выполнение AVFoundation/Photos.

Также PASS: полное применение overlay, Python compile,3существующих теста ресурсов уведомлений, release metadata,13RU Tour strings, diff check. Tree-sitter:25отдельных Swift/ObjC +4изменённых generated Swift. Два прежних `nonisolated(unsafe)` Swift6 в VideoRecorder не поддерживаются грамматикой; ошибки совпадают с baseline, после удаления только этих модификаторов из строки в памяти новых ошибок нет. Native файл не изменён ради парсера.

Apple SDK/typecheck, настоящие AVAssetWriter/Photos, серверная доставка и iPhone недоступны. Новая сборка не запускалась. Причина всех ранее описанных сетевых «часиков» не доказана; устранение всех будущих ошибок не заявляется.

## Приёмка следующего рабочего выпуска

1. По отдельной команде собрать рабочую0.5.4, сохраняя номер при повторных попытках.
2. Проверить10кружков подряд, start/stop/cancel/resume, нехватку места, фон/прерывание/возврат. Сбой освобождает интерфейс; корректные звук/видео сохраняются.
3. MP4/MOV, большие/iCloud видео, отмена,1/Nадресаты и schedule; сравнить SHA256/размер исходника и скачанного файла, воспроизведение в другом клиенте.
4. Save удалённых voice/round: отказ Photos, отсутствие bytes, очистка архива во время операции, реальные сообщения об успехе/ошибке.
5. Регрессия speaker/A2DP/HFP, rear camera, readonly/read/deferred reactions, autoplayOFF/ON, defaults, прокси/VPN и обычной отправки.
