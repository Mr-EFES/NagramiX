# Текущий контекст NagramiX 0.5.3

## Активная задача завершена: сборка и проверенный релиз

Пользователь потребовал отслеживать сборку до успеха и уточнил правило версий: версия повышается для следующего рабочего выпуска, а не для попыток. Текущий выпуск0.5.3 успешно собран и опубликован; следующий рабочий0.5.4. Повторные попытки0.5.3 не повышают версию. Правило закреплено в AGENTS/README/отчёте.

Workflow [№86 / 38176187919](https://github.com/Mr-EFES/NagramiX/actions/runs/38176187919): build и release success. Source SHA/tag target `8c0c117647ae26c444965689773f1ae77a151f99`; docs-only HEAD не подменяет source SHA IPA. Clean build, publish_release=true, prerelease=true, artifact_run_id пустой. [Проверенный IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.3/NagramiX-0.5.3-unsigned.ipa), [релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.3), [доказательства](RELEASE_STATUS.md).

IPA80 924 082байта, SHA256 `8c5028bfb13cbdb1ab1c12449b714901db13eee60fb398504048c59bf3581844`. Скачан в `/tmp/nagramix-053-build86-release`, проверен штатным validate_unsigned_ipa.py, ZIP CRC, всеми6 ARM64 Mach-O, minimum15.0, background audio, RU268/EN194 точными строками,31мелодией, checksum/provenance/run/tag/body. Нативная компиляция подтверждена для всех9 ранее ожидавших функций; device_pending сохранён. XCTest не запускались, аудио/server round trip/сеть/жесты на физическом iPhone не проверялись.

Ошибка предыдущей попытки№85 (ViewController→AlertController) исправлена durable weak property `ViewController?`; source proof436outputs/435unchanged/exact reverse и grammar PASS. Успешный Apple SDK compile№86 подтвердил типы. Auth runtime причину не считать доказанной или устранённой.

Telegram13.0 pin `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`, macOS26/Xcode26.6 release_arm64. Все старые releases/tags/assets сохраняются; новых сборок для документов не запускать.

## Накопленные изменения, которые нужно собрать

- Voice/round end: native playedToEnd, без seek0 и next при OFF; matching view-once screen закрывается, generation guard. «Автопереход голосовых» default OFF, единственный обратный legacy disableVoiceAutoplay key, saved behavior сохранять. [Контракт](DISABLE_VOICE_AUTOPLAY.md).
- Recording с музыкой: atomic mixing category/mode, маршруты speaker/A2DP/HFP, generation/identity guards и отдельные completion pipes. Семь guarded native sources; codecs/upload/enqueue прежние. Причина сетевых часиков после enqueue ещё не доказана. [Контракт](RECORDING_WITH_MUSIC.md).
- Auth notice: account-owned active/cooldown60 guard, canonical RU/EN, safe reason logging. Не восстанавливает серверный ключ, не делает auto logout, не подавляет все server warnings. Одна установка NagramiX рядом с официальным Telegram допустима. [Контракт](AUTHORIZATION_NOTICE_HANDLING.md).
- Profile links: OFF default; emptyID собственный peer отправляющего аккаунта, доступный positive56-bit ID. TextMention cloud, tg://user?id SecretChat, UTF16/entities preserved, only new texts/captions. [Контракт](PROFILE_LINK_MESSAGES.md).
- Settings без footer, согласованные короткие названия, native fonts/sections/search/persisted defaults прежние. [Контракт](CONCISE_SETTINGS.md).
- Original videos ON: unchanged PHAsset resource, native document с Video для MP4/MOV, original bytes/metadata, separate thumbnail/cover, проверенный fast-start. Edited/TTL/GIF/camera прежние. [Контракт](ORIGINAL_VIDEOS.md).
- «Фото без сжатия» ON: standard TelegramMediaImage JPEG100/nativeHD2560, no upscale, без обещания byte identity. Новый highQuality key, legacy original fallback; прежний большой-фото пункт удалён из UI, ключ OFF совместимости сохранён. [Контракт](HIGH_QUALITY_PHOTOS.md).
- Selection toolbar в readonly avatar preview: gate ПОСЛЕ native selection/report, ДО subscriber/composer. 1/N выбранных, delete/export/три пересылки без активации, только Reply открывает normal chat. Обычная переписка исправна, прежний provisional обычный refresh исправление удалено. [Контракт](MESSAGE_SELECTION_ACTIONS_FIX.md).
- «Непрочитанные сверху» точное финальное название, Интерфейс/Чаты ID139, `nagramix.interface.unreadChatsFirst` absent ON/saved OFF сохранять. Все обычные папки/архив unpinned по actual unread count DESC, tie native index, mute ignored, pinned/promo/contact/header slots прежние. Adaptive native tail80→160… после holes, cancel superseded subscription, count guard; snapshot rank Comparable/equality, OFF native paging, ON exact index scroll. Pickers/topics/поиск/read/send/readonly прежние. [Контракт](UNREAD_CHATS_FIRST.md).

## Предварительная проверка

Clean proof `/tmp/nagramix-051-prebuild-20261011-proof` полностью совпал с `/tmp/nagramix-051-unread-first-complete-proof`:436outputs. Относительно последнего preview-selection baseline427byte-identical,9целевых изменений (5settings/locales,4native list). Grammar7без ошибок. `scripts/validate_unread_chat_overlay.py`:16reverse exact,4drift+rerun rejected before writes. Pythoncompile/JSON/metadata/diff pass. Sparse raw fixture `/tmp/nagramix-051-recording-continuity-raw`, audit `/tmp/nagramix-unread-audit`; proof paths технические, не версия нового IPA. Полный pipeline применяет durable overlay `ios/`, не temporary source. Все новые реализации скомпилированы в№86: compile_passed/device_pending. Все накопленные пользовательские изменения сохранены.

Следующий шаг — физическая проверка0.5.3/build86 по [плану](IPHONE_TEST_0.5.3.md). IPA требует внешней подписи. По результатам теста исправлять только подтверждённые пользовательские ошибки; новый рабочий выпуск повышает patch до0.5.4. Документация/статусы обновлены после независимой проверки, дополнительная компиляция не требуется.
