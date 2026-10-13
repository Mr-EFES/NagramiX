# Текущий контекст NagramiX 0.5.4

## Активная задача: чистая сборка0.5.4 для iPhone

Пользователь13октября2026разрешил новый рабочий выпуск со всеми подготовленными правками и тестовым релизом. Версия workflow/registry/README/LICENSE/gitignore/аннотации/плана0.5.4; повторы сохраняют0.5.4, следующая рабочая0.5.5. Upstream CURRENT. Перед dispatch выполняются проверки исходников и фиксация/push в main. Run/source SHA и результат — [статус](RELEASE_STATUS.md); старые releases/tags/assets сохранить. Нового IPA пока нет.

Все предыдущие ниже записи «без commit/push/build» относятся к состоянию на момент отдельных задач, а не к текущей разрешённой сборке. Новые compile_pending остаются до результата Xcode. Проверенный full proof453/449byte-identical после аудита в `/tmp/nagramix-stability-audit-final-checked-proof`; тест на iPhone ожидается. Следить за run до успеха, исправлять только конкретные ошибки компиляции/упаковки; не скрывать физические риски.

## Аудит стабильности — исправления в исходниках

По запросу пользователя проверены собственный overlay и критические native пути. [Отчёт/ограничения/приёмка](STABILITY_AUDIT.md). Три подтверждённые ошибки: private `.file` вызовы из двух других файлов (Swift typecheck); бесконечный writer readiness wait (блокирует stop/cancel/таймер); asynchronous MediaBox move гоняется с очисткой Photos temp. Save helpers используют public prepare; поздний SHA-guarded apply_recorder_backpressure_fix ограничивает ожидание2секундами, отменяет неисправный writer/очищает pending audio и учитывает video append failure; OriginalVideos синхронно pin/copy в отдельный путь перед прежним native queued move. Resource type/bytes/metadata/defaults/read/protected features сохранены.

Чистый proof `/tmp/nagramix-stability-audit-final-checked-proof`:453files,449unchanged/4изменения относительно call-rating proof. Tracked `scripts/validate_stability_overlay.py`:4reversals, drift/rerun before writes, настоящая ФС hardlink/copy раннего удаления PASS.25standalone syntax +4generated Swift PASS с учётом двух прежних Swift6 nonisolated(unsafe), неподдерживаемых tree-sitter; Python/3unit tests/metadata/13RUintro/diff PASS. Audit `/tmp/nagramix-stability-audit-native` содержит blob-verified Fetch/TempBox. SDK/typecheck/device недоступны; все причины сетевых clock не доказаны. Registry recorder_keep_music/original_videos compile_pending для working tree; компиляция прежней реализации в build86 остаётся фактом.

Нет commit/push/build. Предыдущие рабочие задачи сохранены; опубликованный0.5.3/build86 не подменён. Следующий шаг по отдельной команде —0.5.4 и приёмка из отчёта. Не обещать отсутствие всех будущих ошибок.

## Новая задача: не спрашивать оценку звонка

По референсу пользователя добавлен checkbox Функции/Звонки: skipRating absenttrue, savedfalse/true сохраняются. Shared Foundation NagramiXCallSettings key nagramix.calls.skipRating, Core current/model/save и UI stableId140/position515 (139 уже unreadChatsFirst). Поиск title+synonyms, footer отсутствует. [Контракт](SKIP_CALL_RATING.md), registry skip_call_rating compile_pending/device_pending.

Аудит обнаружил NodeV2 не вызывал существующий presentCallRating callback. В `.terminated` сохранён callEnded(reportRating), добавлен callback только при reportRating+реальном CallId/isVideo. Common CallController suppress guard до scheduling и непосредственно перед native0.5sec presentation. OFF возвращает native automatic factory; ручной ChatController rateCall(userInitiated:true), рейтинг API, termination/debug/transport не модифицированы. Никакого принудительного popup для reportRatingfalse или fake stars.

Последний apply_skip_call_rating:3SHA inputs/5 in-memory уникальных замен, CallsUI зависит только от существующего Foundation-only MediaSettings. Proof `/tmp/nagramix-053-call-rating-checked-proof`:453outputs/444unchanged/8changed+1new относительно expanded452 (archived-save449+3native call inputs). `/tmp/nagramix-validate-call-rating.py`:5exact reversals,3drift+rerun before writes, uniqueIDs/RUEN/search, manual/archive paths byte-identical PASS; grammar6Swift PASS, metadata/Python/diff PASS. API audit `/tmp/nagramix-call-rating-audit` содержит PresentationCallManager/Controller/NodeV2/Node/RatingController. SDK/typecheck/server/iPhone не проверены.

Без commit/push/build, версия/релиз0.5.3/build86 прежние, предыдущие незакоммиченные задачи сохранены. Следующая рабочая сборка0.5.4 только по отдельной команде.

## Новая задача: сохранить звук/видео из архивного меню

По четырём скриншотам пользователя удалённые voice/round теряли native Save actions. Root cause: archive branch actions.removeAll() пересобирала только локальные edit/forward/select/delete. Добавлен helper nagramiXArchivedSaveMediaActions только в эту ветку; защищённые/secret media и coarse eligibility обычного звука сохраняются. «Сохранить звук» именно native notification library (это действие из референса); видео — Photos. [Контракт/приёмка](ARCHIVED_MEDIA_SAVE.md), registry archived_media_save compile_pending/device_pending.

Core NagramiXArchivedSoundSave читает bounded ≤1MB полную независимую копию на worker, native _internal_uploadNotificationSound получает optional mimeType(default прежний MPEG, архивный OGG точно OGG), ошибки и cache обновляются native. Никаких stale deleted IDs. UI NagramiXArchivedMediaSave pin/copy в EngineTempBox MP4/MOV перед DeviceAccess/Photos; success только от performChanges, cleanup после отказа/ошибки/завершения, включая disposal. Предыдущий NagramiXArchivedMediaCopy теперь также обеспечивает явно запрошенный export; его storage/playback/ID контракты не изменены. На источник preview/save/read/reactions новых вызовов нет.

apply_archived_media_save перед call rating helper:2full SHA inputs/3 уникальные замены в памяти +2 helpers с conflict guard. Чистый proof `/tmp/nagramix-053-archived-save-proof`:449outputs/442unchanged/5changed+2new относительно onboarding447. Validator `/tmp/nagramix-validate-archived-save.py`:3reverse восстанавливают2 native источника,2 drift+rerun+helper conflict before writes; hardlink/copy/mmap владение при unlink PASS, RU/EN keys unique PASS; grammar5Swift PASS и onboarding validator PASS. Pinned audit `/tmp/nagramix-archived-save-audit`:NotificationSoundList/SaveToCameraRoll/NotificationSoundSelection/Queue. Native SDK/Photos/server/device не проверены.

Все изменения только working tree, без commit/push/build. Предыдущие swipe/archive-transfer/proxy/onboarding сохранены; опубликованный0.5.3/build86 прежний. Следующая рабочая версия0.5.4 только по отдельной команде.

## Новая задача: приветственные экраны NagramiX

По запросу пользователя заменены6 Tour titles/descriptions RU/EN, логотип,5 иллюстраций преимуществ и телефон на вводе номера. Источник текстов ios/Resources/Onboarding/copy.json. Первая иллюстрация побайтно основная branding/AppIcons/1.png; новый RGBA atlas1536×1024 получен ImageGen, ячейки512×512 извлекаются CoreGraphics при загрузке. PNG ресурсы проверяются manifest SHA и явно добавлены в main app resources.

Новый apply_nagramix_onboarding перед archived_media_save:4 full-SHA inputs/24 замен в памяти, BUILD допускает ровно известные branding display-name/language substitutions top-level apply_overlay. UIView+UIImageView карусели сохраняют native layout/text/fonts/button/start auth callbacks; offset-linked transition, Reduce Motion, UIKit snapshot; GL renderer/60fps timer не запускается. Phone ASImageNode100×100 сохраняет layout, старые animatedPhone visual callbacks удалены, остальные auth/QR/passkey/country/phone callbacks прежние. Общий public UIKit loader в RMIntro, уже существующая AuthorizationUI dependency. [Контракт/приёмка](BRANDED_ONBOARDING.md).

Proof `/tmp/nagramix-053-onboarding-final-proof`:447outputs/438unchanged/6changed+3new относительно `/tmp/nagramix-053-onboarding-baseline`444 (proxy proof440+4 audited native inputs). Validator `/tmp/nagramix-validate-onboarding.py`:24 точных reversals для4 native input,4 drift+rerun+asset corruption/conflict before writes, реальный CI branding accepted,26 uniqueRU/EN strings PASS. Fake ZIP verifies upcoming IPA asset/copy checker, grammar Swift+2ObjC PASS, prior proxy/archive validators PASS. SDK/typecheck/real IPA bundle/physical UI не проверены; registry branded_onboarding compile_pending/device_pending. Никаких commit/push/build; опубликованный0.5.3/build86 и прошлые правки сохранены. Новая команда на0.5.4 получена13октября; прежний результат проверок сохранён ниже.

## Новая задача: состояние прокси-чекбоксов и отдельный DNS Telegram

Последнее уточнение пользователя: автопереключение ON при двух и более прокси, DNS Telegram отдельным пунктом сразу после Системного. [Контракт](PROXY_VPN_AND_LAYOUT.md). Правка только в working tree, без commit/push/build; текущий IPA0.5.3/build86 прежний. Registry dns_doh/proxy_failover/proxy_vpn_bypass compile_pending/device_pending.

Root cause VPN: callback писал global defaults, но cached controller ValuePromise оставался прежним. Late helper apply_proxy_settings_sync_fix после архивного helper, перед онбордингом: полный SHA native ProxyList +13 замен в памяти, local updater и lifecycle notification signal, явный OFF сохраняется. Новое Foundation-only NagramiXProxyPreferences в уже подключённом MediaSettings: absent VPN ON при enabled+activeServer+непустом списке; absent auto ON только ≥2 разных серверов; timeout15. Savedfalse не мигрировать, в том числе legacyfalse. Core observer и UI activation используют один initializer; unconditional auto=true удалены, unrelated full-save не материализует absent proxy defaults.

DNS system0/default сохранён, telegram7 добавлен вторым, прежние1–6 стабильны. Explicit native picker дополнен; Swift/ObjC switches знают7. Оба native choices используют прежний MTProtoKit resolver, отдельный Telegram endpoint не придуман. Полный clean proof `/tmp/nagramix-053-proxy-sync-final-proof`:440outputs/432unchanged/7changed+1new относительно архивного439. `/tmp/nagramix-validate-proxy-sync.py`:13 exact reversals, drift+rerun before-write, picker/locales PASS; grammar5PASS, архивный validator PASS. SDK/typecheck/device не проверены. Следующая сборка только по отдельной команде, рабочая версия0.5.4.

## Новая задача: исправление архивного «Переслать без» и рассылки

Реализовано после физического сообщения пользователя о build86. Подготовленная задача свайпов сохранена без изменений. Все правки только в working tree, commit/push/build не выполнялись; версия и опубликованный IPA прежние. [Контракт/приёмка](ARCHIVED_MESSAGE_TRANSFER_FIX.md), forward_copy registry compile_pending/device_pending.

copyToSingleRecipient теперь использует native одиночный picker и destination chat draft (включая Saved/topic), никакого enqueue при выборе. ChangeRecipient архивного draft остаётся одиночным. Native preview/accessory/options/cancel имеют fallback на archive snapshots. При Send Node создаёт .message из snapshot вместо .forward deleted ID; metadata/album/caption и обычные forwards прежние. Предлагаемый автор архивного original не имитируется. Source readonly/reaction gates прежние.

NagramiXArchivedMediaCopy — отдельный outgoing helper в TelegramCore/Utils: full local primary обязательна, новые LocalFile/LocalImage IDs, никаких stale cloud references; optional thumbnails/cover только полные. Temp hard links pin bytes до native upload, fallback copyItem; staged rollback при неуспехе. Понятная RU/EN ошибка до enqueue, исходный draft остаётся. Рассылка прежняя multiple/native payment/silent/schedule/topic/correlation flow. Конкретная server/network причина всех clock по скриншоту не установлена.

apply_archived_copy_send_fix перед proxy sync helper:6full SHA inputs/24in-memory substitutions до записи. Полный proof `/tmp/nagramix-053-archive-copy-final-proof`:439outputs/429unchanged/9changed+1new относительно `/tmp/nagramix-053-archive-copy-baseline` (settings swipe baseline +2audited native inputs). Validator `/tmp/nagramix-validate-archive-copy-fix.py`:24exact reversals,6drift+rerun before writes PASS; Swift grammar7PASS, filesystem hardlink ownership PASS, RU/EN unique, metadata/Python/diff PASS. Native source/API audit `/tmp/nagramix-archive-transfer-audit`; retained storage/cache/player/recording/Enqueue core побайтно прежние.

SDK/typecheck и физическая отправка не проверены. Следующий шаг по отдельному запросу — новый рабочий выпуск с patch+1 и приёмка архивных text/photo/voice/round/view-once, выбор1/N, смена адресата, Send/quiet/schedule/topics/payments, недоступный primary, очистка архива после enqueue, readonly и live+archive. Публикацию build86 и её sourceSHA не подменять текущим working tree.

## Новая задача: свайпы категорий настроек — исходники подготовлены

По запросу пользователя добавлены свайпы между Интерфейс/Функции/Прочее. Новая правка только в рабочем дереве после build86, без commit/push/dispatch; опубликованный IPA и версия0.5.3 не менялись. Изменён только tracked NagramiXSettingsController.swift: local ItemListController subclass со штатным direction-aware pan, shared selection для tap/swipe, no wrapping, левый край Back, exclusions UIControl/text/slider, глобальный непустой поиск disables, commit только ended/порог либо flick. На границе центральный свайп поглощается, чтобы вместо предыдущей категории не сработал Back. Темы/шрифты/размеры и persisted keys/defaults/actions прежние.

[Контракт/приёмка](SETTINGS_CATEGORY_SWIPE.md); добавлены product/features/settings-category-swipe.md и отдельная registry запись implemented/compile_pending/device_pending. README/каталог обновлены; уже опубликованный релиз не переписывать.

Pinned API audit: public open ItemListController.loadDisplayNode, inherited PresentationDataUtils convenience initializers, InteractiveTransitionGestureRecognizer center/edge/control filtering, NavigationContainer требует failure для другого UIPan, но не для InteractiveTransition. Локальный delegate задаёт приоритет центрального pan; native Back с края не изменяется. Audit `/tmp/nagramix-settings-swipe-audit` по exact blob SHA. Глобальные ItemListUI/Display не менялись.

Полный overlay proof `/tmp/nagramix-053-settings-category-swipe-final-proof`:436outputs/435unchanged, единственное отличие SettingsUI/NagramiXSettingsController.swift. Swift grammar/metadata/diff checks PASS; native Apple SDK отсутствует, UIKit поведение и новая нативная компиляция не проверены. Следующий шаг: по отдельному запросу собрать следующий рабочий выпуск с patch+1 и проверить сценарии из контракта. Без команды новую сборку не запускать.

## Предыдущая завершённая сборка: build86

Пользователь потребовал отслеживать сборку до успеха и уточнил правило версий: версия повышается для следующего рабочего выпуска, а не для попыток. Предыдущий выпуск0.5.3 успешно собран и опубликован; это не исходный SHA нового0.5.4. Правило закреплено в AGENTS/README/отчёте.

Workflow [№86 / 38176187919](https://github.com/Mr-EFES/NagramiX/actions/runs/38176187919): build и release success. Source SHA/tag target `8c0c117647ae26c444965689773f1ae77a151f99`; docs-only HEAD не подменяет source SHA IPA. Clean build, publish_release=true, prerelease=true, artifact_run_id пустой. [Проверенный IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.3/NagramiX-0.5.3-unsigned.ipa), [релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.3), доказательства сохранены в Git до смены текущего отчёта.

IPA80 924 082байта, SHA256 `8c5028bfb13cbdb1ab1c12449b714901db13eee60fb398504048c59bf3581844`. Скачан в `/tmp/nagramix-053-build86-release`, проверен штатным validate_unsigned_ipa.py, ZIP CRC, всеми6 ARM64 Mach-O, minimum15.0, background audio, RU268/EN194 точными строками,31мелодией, checksum/provenance/run/tag/body. Нативная компиляция подтверждена для всех9 ранее ожидавших функций; device_pending сохранён. XCTest не запускались, аудио/server round trip/сеть/жесты на физическом iPhone не проверялись.

Ошибка предыдущей попытки№85 (ViewController→AlertController) исправлена durable weak property `ViewController?`; source proof436outputs/435unchanged/exact reverse и grammar PASS. Успешный Apple SDK compile№86 подтвердил типы. Auth runtime причину не считать доказанной или устранённой.

Telegram13.0 pin `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`, macOS26/Xcode26.6 release_arm64. Все старые releases/tags/assets сохраняются; новых сборок для документов не запускать.

## Изменения, включённые в опубликованный build86

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

Следующий шаг — физическая проверка0.5.3/build86 по [плану](IPHONE_TEST_0.5.4.md). IPA требует внешней подписи. По результатам теста исправлять только подтверждённые пользовательские ошибки; новый рабочий выпуск повышает patch до0.5.4. Документация/статусы обновлены после независимой проверки, дополнительная компиляция не требуется.
