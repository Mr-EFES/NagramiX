# Анимация первого и повторного удаления

Исправление по видео `-197865056217929454.mp4` (38,03с,384×832,30fps). Контрольные кадры показывают: первое удаление пяти сообщений примерно12,6с сразу оставляет полупрозрачные архивные записи с меткой; повторное примерно31с запускает dust и убирает записи. Содержимое личной переписки и коды не переносятся в документацию.

## Причина

Предыдущая `archive_deletion_visibility` защищает локальную копию от isHidden и ложной задержки схлопывания. Она исключает из настоящих deletion candidates сообщения с теми же логическими IDs, что в следующем отображении. Это устранило пустое место, но одновременно подавило dust при первом native→archive переходе.

## Изменение

Новая поздняя guarded стадия `archive_deletion_effect` после `pip_visual_handoff`: один replacement `ChatHistoryListNode.swift`,13guards. Старые canonical snapshots сохранены. Сравниваются прежние живые MessageId и новые сообщения с публичным NagramiXArchivedMessageAttribute, включая пятиэлементные tuples альбомов. Пересечение — событие первого удаления. Оно определяется по логическому ID(peer/namespace/id), независимо от stableId и от отметки интерактивного удаления в engine. Поэтому работают неизменившийся stableId, уже обновлённая ячейка, серверное обновление и non-animated history transition.

Для первого удаления добавляется один штатный dust snapshot на ячейку/альбом. Сама локальная копия не скрывается и не получает0,8с длительности удаления; её прежний renderer показывает50% содержимого и метку под уходящим снимком. Геометрия, хранение, сортировка, Undo, подписи, grouped attachments и альфа не меняются. При настоящем повторном удалении остаются прежние dust/isHidden и фактическое схлопывание. Смешанный batch анимирует оба вида, но длительность/hidden ownership назначает только исчезающим ячейкам.

Первичная загрузка архива, прокрутка, обновление текста/ASR/метки и смена stableId уже архивной записи не повторяют анимацию. После Undo новое удаление снова анимируется. OFF сохраняет штатный путь без dust и без отложенного проигрывания после включения. Native killswitch, служебные/слишком высокие ячейки, snapshot fallback и scheduled исключения прежние. Задержанная копия восстанавливается прежним weak ownership helper без второй анимации уже исполненного удаления. Сторонний владелец скрытия не подменяется.

Строки UI/настройки/defaults и ключ nagramix.chats.deletionEffectEnabled прежние. Не изменяются архив, пересылка/рассылка, временные сообщения/ASR, renderer с50% и notice, PiP или существующие backend-layout методы. Точные13guards и побайтная проверка всего вне transition защищают эти границы.

## Проверки

`validate_archive_deletion_effect.py` выполняет фактический transition и прежние weak/dust helpers.210 новых assertions +61 прежняя проверка зазора/visibility в debug и-O;9 отрицательных вариантов в обоих режимах отвергают отсутствие первого эффекта, старый gate, скрытие копии, ложное схлопывание, зависимость от stableId, повтор архивного обновления, initial-load эффект, игнорирование OFF и повторный снимок альбома.38 повреждённых входов/шаблонов/путей отвергнуты до записи. Полный изменённый Swift файл прошёл frontend parse. UIKit/CA, snapshot, renderer и engine IO — явные границы, физическая отрисовка не подтверждена.

Проверены1/2/5 сообщений, отдельные строки/альбомы, оба stableId варианта, animate flag ON/OFF, первое/повторное удаление, initial/reappearing архив, mixed live/archive batch, OFF→ON, отсутствие snapshot, killswitch, другая namespace/peer, external hidden owner и Undo→повтор. Старые validators разворачивают новую стадию по точным SHA без ослабления guard checks. Guard-only compatibility пройдена для PiP, меню моделей, visibility, temporary actions, message copy и archive lifecycle;71×613 каталоги и source localization contract сохраняются без новых строк.

Свежая композиция pinned13.1.2+legacy13.0 прошла; после точного7-file post-port совпала с incremental по602owned paths. От последнего проверенного source отличается только разрешённый ChatHistoryListNode. PostboxImportCheck проходит. Отчёты `/tmp/nagramix-archive-first-delete/{validation.json,composition.log,final-composition-hashes.json}`. Dummy API configuration используется только для source checks, не для IPA.

**Статус: source_checked / native_compile_pending / device_pending.** В опубликованной0.8.7/build173 этой новой правки нет; опубликованные файлы и теги не менялись. SDK/Actions/rerun/IPA/commit/push не выполнялись, новая сборка требует отдельной личной команды владельца.
