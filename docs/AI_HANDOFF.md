# Текущий контекст NagramiX 0.5.3

## Активная задача: новая сборка после ошибки компиляции

Пользователь спросил результат; [№85](https://github.com/Mr-EFES/NagramiX/actions/runs/38166584585) из `6d7407102c754c6b7c86503525fd874a55a26574` FAILED. Build job114550292433, release skipped, IPA отсутствует. Compiler `ApplicationContext.swift:791:65` — ViewController cannot assign to AlertController. CLI logs redirect Azure Forbidden; GitHub connector `fetch_workflow_job_logs` успешно дал журнал, единственная ошибка типов (две одинаковые diagnostic строки).

Исправлен только durable weak property на `ViewController?`, соответствующий реальному factory return type. Полный clean overlay436outputs/435unchanged, exact reverse и grammar PASS; proof `/tmp/nagramix-053-auth-controller-fix-proof`. Не исправление runtime auth key, native Cancel/Logout/dedupe прежние.

Постоянное правило: каждая НОВАЯ компиляция повышает patch-версию на1, включая retry. Теперь0.5.3, следующая0.5.4, затем0.5.5. Не rerun0.5.2. В рамках продолжаемой задачи получения тестового IPA готовится clean0.5.3 с сохранением всех функций и старых releases/tags/assets. Version synced workflow/registry/current docs/notes/README/LICENSE/.gitignore. Ветка main, один workflow, clean_build=true/publish_release=true/prerelease=true/artifact_run_id пустой. [Статус](RELEASE_STATUS.md), [план](IPHONE_TEST_0.5.3.md). Новый SHA/run ещё не записаны; до success не объявлять IPA готовым.

Официальный Telegram13.0 pin `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`, iOS15.0. Последний опубликованный IPA №84 из `7b8137a6d68554b1790322f8ab1f03460ff7823c` не содержит новых функций. Apple SDK отсутствует на Linux, Actions macOS26/Xcode26.6 release_arm64.

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

Clean proof `/tmp/nagramix-051-prebuild-20261011-proof` полностью совпал с `/tmp/nagramix-051-unread-first-complete-proof`:436outputs. Относительно последнего preview-selection baseline427byte-identical,9целевых изменений (5settings/locales,4native list). Grammar7без ошибок. `scripts/validate_unread_chat_overlay.py`:16reverse exact,4drift+rerun rejected before writes. Pythoncompile/JSON/metadata/diff pass. Sparse raw fixture `/tmp/nagramix-051-recording-continuity-raw`, audit `/tmp/nagramix-unread-audit`; proof paths технические, не версия нового IPA. Полный pipeline применяет durable overlay `ios/`, не temporary source. Новые реализации compile_pending/device_pending до Actions/device. Все накопленные пользовательские изменения сохранены.

Исходники сохранены и normal push main выполнен. Следующий шаг: commit+normal push main, dispatch новой версии0.5.3, проверить новый workflow, исправить ошибки в авторизованном scope при необходимости (НО новая компиляция = следующая patch-версия), проверить IPA checksum/provenance/version/build/MachO/resources, записать SHA/run/release link/компиляцию. После успешного run допускается docs-only checkpoint без повторной сборки; source SHA IPA не подменять docs SHA. Для физического теста требуется внешняя подпись (SideStore).
