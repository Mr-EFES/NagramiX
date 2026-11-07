# Команды воспроизведения системного PiP

**Состояние выпуска:** перенесено на Telegram13.2 и включено в успешный0.8.9/build185: `compile_passed / package_verified / owner_published / device_pending`. [SDK, IPA, hashes и релиз](RELEASE_STATUS.md); [приёмка на iPhone](DEVICE_CHECK_089.md) ещё ожидается. Далее — исходный контракт и история локальных проверок до публикации.

По отдельной команде владельца исправлена R3 проверки от 6 ноября. Это согласованное точечное отклонение от playback callback Telegram 13.1.2. Штатный механизм PiP, быстрый свайп, окно, анимации входа/возврата и исправления R1/R2 сохранены. SDK/Actions/IPA, commit/push и публикация не запускались.

## Поведение

Прежний `setPlaying` игнорировал аргумент и всегда вызывал `togglePlayPause()`. Повторная команда Play останавливала уже играющее видео, а Pause могла запускать остановленное.

Теперь `setPlaying(true)` вызывает `UniversalVideoNode.play()`, а `false` — `pause()`. Оба существующих API адресуют текущий content ID через штатный manager и передают команду текущему видеоплееру. Повторные вызовы устанавливают требуемое состояние. В обработчике нет сравнения с запаздывающим status и переключения по его значению: команды передаются и при буферизации или отсутствии первого status. Поэтому последовательность Play/Pause не теряет последнее намерение пользователя до очередного сообщения от движка. Позиция и исходный видеослой не заменяются; перемотка, новый decoder и новая загрузка не добавлены.

Сама сигнальная подписка, системный paused query, seek/skip, lifetime controller/delegate, native setup, кнопка, быстрый свайп и restore остаются прежними. Единственный production diff — тело указанного callback. Утверждённый ранее полный native snapshot сохранён как исторический неизменяемый вход.

## Стадия и проверки

Поздняя `pip_playback_commands` после `round_caption_transport`: один replacement, 12 guards, два Before/After шаблона. Guards фиксируют остальные native GalleryUI outputs, R1/R2 outputs, BUILD и API плеера. Все зависимости, SHA и пути проверяются до первой записи. Новый validator первый в workflow; 25 прежних validators снимают позднюю стадию по точным SHA, сохраняя исходные проверки и команды.

`validate_pip_playback_commands.py` исполняет полный production playback delegate и настоящие тела `UniversalVideoNode.play/pause/togglePlayPause`. AVKit, поиск контента, decoder и доставка status являются явными границами. Проверены Play/Pause из playing, paused, обоих вариантов buffering и без status; тройные повторные команды; противоположные команды до публикации статуса; внешнее изменение статуса; сохранность позиции, ID, слоя и controller; команды после возврата и повторного входа в PiP. Прежние 37 native-сценариев также выполняются на текущем исправленном controller.

В каждом debug и `-O` прошли 113 новых, 37 native, 118 R2 и 48 R1 проверок. Три отрицательных варианта на режим воспроизводят старый безусловный toggle, toggle с проверкой cached status и инверсию команд. Всего 14 исполнений; 36 loader-сценариев отказа до записи и parse полного изменённого Swift-файла прошли.

Strict localization без исключений: 71 язык × 613 ключей, 112 файлов настроек/debug, 594 обращения и по 43 621 runtime-проверке на режим. Новых UI-строк нет. Исторические snapshots при малом свободном месте используют read-only hard links, без изменения проверок или SHA.

Обратное снятие R3/R2/R1 прошло прежние source-контракты. После возврата только согласованного callback все 13 замороженных native-блоков совпали с эталоном. Полная final post-port композиция проверена по SHA: 33 964 файла, ровно одно ожидаемое изменение относительно R2; все остальные файлы идентичны. Предыдущий полный source R2 сохранён, изменяемые outputs отсоединены от hard links до записи. Семь final post outputs, PostboxImportCheck, metadata, Python AST и diff проверены.

## Статус

R1/R2/R3 исправлены локально. Pre-post проекция `/tmp/nagramix-pip-playback-commands/working`, 620 путей; полный final source `/tmp/nagramix-pip-playback-commands/source`. Предыдущий `/tmp/nagramix-round-caption-transport/source` неизменён. Reports `validation.json`, `previous-stage-compatibility.json`, `final-source-proof.json`, `final-source-hashes.json`, `localization.log`, `task-state.json` рядом.

Остаются `compile_pending/device_pending`. Локальные проверки не подтверждают реальную AVKit/UIKit работу или плавность на iPhone. Новая сборка запускается только по отдельной команде владельца. Версия, upstream pin, README/LICENSE и опубликованный IPA 0.8.8/175 прежние.
