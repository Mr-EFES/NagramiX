# Автоматическая тихая отправка

Включено в Release0.6.9/build122 на Telegram13.1.1: native_compile_passed/package_verified/device_pending. [Проверенный пакет](RELEASE_STATUS.md). Ниже — исходный контракт и история source-проверок.

Пользователь22октября запросил чекбокс «Отправлять без звука» в Функции → Сообщения, fresh ON и сохранение пользовательского выбора. Реализовано в main: **source_checked / native_compile_pending / device_pending**. IPA114 без этой функции; сборка/commit/push не запускались.

Foundation-only `NagramiXSendSettings` в существующем NagramiXMediaSettings читает новый отдельный ключ `nagramix.messages.sendSilently`, absent→true; setter пишет только явное значение. Нет startup reset или изменения существующих snapshots. SettingsUI: `.sendSilently(Bool)`, stableID158/position351, native multiline ItemListSwitchItem, RUEN/search. Callback сохраняет значение и обновляет settingsPromise. Остальные ID/defaults прежние.

В общей transactional `enqueueMessages` один раз читается настройка для batch. `nagramiXSilentSendMessage` меняет только outgoing attributes. Native фильтры обычной/пересланной отправки сохраняют NotificationInfoMessageAttribute; PendingMessageManager переводит `.muted` в silent bit5. Механизмы загрузки медиа, проверок прав/платежей, read boundaries и очереди прежние.

`nagramiXSilentSendAttributes` при ON объединяет существующие notification flags с `.muted`, оставляет один notification attribute и сохраняет все прочие атрибуты. Personal/automatic и неизвестные native bits не теряются. OFF возвращает исходный массив, включая ручной muted. Повторное применение не создаёт дубликатов.

`standaloneSendEnqueueMessages` сохраняет native isSilent, добавляя к нему общий default. В `standaloneSendMessage` на входе фиксируются преобразованные attributes. Его private `sendMessageContent` ранее не обрабатывал NotificationInfo: добавлена штатная ветка `.muted`→bit5 для text/media RPC. Остальные flags, reply/thread, schedule, fees и ошибки прежние.

Политика не меняет payload, forward source, тему, reply, альбомную группировку, entities, one-shot TTL, оплату или расписание. Уже созданные queued attributes сохраняются после переключения настройки. Служебные действия, истории, звонки и редактирование сообщений не превращаются в новые отправки. Новых dependencies/модулей нет.

## Overlay и проверка

Финальный `ios/silent_send.py`/JSON после `apply_free_screenshot_title`:8 SHA guards,19 exact operations,2 source globs,1 provided helper MediaSettings и1 новая копия TelegramCore. MediaSettings helper копируется существующей общей стадией Sources; Core helper добавляется после всех проверок. Все guards/helpers/anchors проверяются до первой записи стадии. Прежняя immutable цепочка сохранена.

Full overlay Telegram-iOS13.0 f1dd7a2:439 outputs; стадия меняет6 native файлов и добавляет1 Core helper,432 остальных inputs прежние. Provided MediaSettings helper также новый относительно исходного состояния задачи. Два дополнительных inspected pinned файла (StandaloneSendMessage и NotificationInfo) сверены по Git blob SHA, находятся вне repo как fixture.

`scripts/validate_silent_send.py` и `scripts/tests/NagramiXSilentSend{Boundary,Tests}.swift`: **218 checks debug и optimized**, warnings-as-errors; **12 отдельных холодных процессов** с настоящим UserDefaults (test-only synchronize перед немедленным завершением Linux процесса). Проверены absentON/явныеOFF/ON, реальный callback настроек/settingsPromise, native enqueue tuple mapping, share/manual paths, direct standalone RPC bit, native flags encode/decode, idempotency и сохранение payload/thread/reply/grouping/TTL/schedule/fee/прочих attributes. UI/Postbox/media/network — controlled boundaries, методы и ветви извлечены из текущего production source.

**45 fail-closed** сценариев без частичной записи: hashes/provided drift, все anchors, missing/empty helpers, copy collision, source globs и reapply. Swift grammar затронутых/новых файлов, Python AST и metadata/diff проходят. Proof `/workspace/.codex-validation-nagramix-silent-send/verification-final.json`; fixture `native-silent-send-final`.

Apple SDK и физическая доставка не проверялись. После отдельной команды на IPA проверить с другого клиента: отсутствие звука и наличие уведомления при ON, обычную отправку при OFF, ручную тихую при OFF; текст/медиа/voice/round/one-shot/альбом/репост/рассылку/темы/standalone sharing, перезапуск с сохранённым OFF/ON, schedule/платежи. Сравнивать ON/OFF при одинаковых настройках уведомлений получателя.
