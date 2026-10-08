# Текущий контекст NagramiX 0.4.7

Обновлено 2026-10-08 (Europe/Moscow). Единственная рабочая ветка — main. Пользователь прямо поручил собрать 0.4.7 для физического iPhone 17 Pro Max / iOS 27.0 / SideStore. Сохранение подготовленных изменений в main, нативная сборка и публикация тестового релиза с русской аннотацией разрешены. Чистая нативная сборка №77 и публикация прошли успешно; опубликованный IPA скачан и проверен. Физическая проверка не выполнена. Последний stable/latest 0.4.5, его релиз/тег/файлы сохранять.

## Авторитетные исходники и выпуск

Проект — overlay. База Telegram-iOS 12.9.2, pin 6ad963e5b62d354da79040f388ae2b9132fb17b8. Перед запуском scripts/check_upstreams.py --platform ios --require-current подтвердил CURRENT. Не обновлять pin автоматически. Единственный workflow .github/workflows/build-unsigned-ipa.yml, NAGRAMIX_VERSION=0.4.7. Текущий выпуск получен новой clean_build=true компиляцией, artifact_run_id пустой, publish_release=true, prerelease=true, main. Прежний артефакт не переиздавался. Новую сборку запускать только по следующей команде пользователя. Русская аннотация — product/releases/0.4.7.md.

Все изменения должны быть в ios/overlay/scripts/документации, не только во временном Telegram checkout. Linux не имеет Xcode/Swift toolchain; полная компиляция только на macOS в workflow. gh использует унаследованный proxy и разрешение network; секреты не читать/не публиковать. Отчёт о запуске/результате дополнять в [RELEASE_STATUS.md](RELEASE_STATUS.md) и этом файле. Не заявлять успешный выпуск до проверки run/source SHA/checksum/версии/ARM64/RU/signature stripping.

## Состав новой версии

### Компактная плотность

apply_compact_chat_list: только геометрия обычной строки, аватар 36, title/preview/date 15/14/12 штатными Font, отступ 5 с масштабированием, minimum height 48 по измеренному содержимому. rawContentRect/правые статусы согласованы; OFF возвращает прежние значения. Ключ/default OFF/перепривязка кэшированных папок не менялись. [Описание](../product/features/compact-chat-list.md).

### Разделение удержания

apply_chat_hold_routing: исходная область ContextGesture сохраняется до scaling по реальному AvatarNode. ON: удержание аватарки → stock preview без прочтения, остальной строки → ContextController location с stock actions generators без preview. Боковые reveal actions подавлены, folder pan из любой области и короткое открытие сохранены. OFF stock. Меню, права/подтверждения и accessibility не переписаны. Ключ/default ON/stable IDs прежние; RU/EN пояснение обновлено. [Описание](../product/features/chat-actions-on-hold.md).

### Полные файлы архива и временные сообщения

NagramiXArchivedMediaStore.swift копируется в TelegramCore/Sources/Utils и включается существующим BUILD glob, новых зависимостей нет. Изучены фактические MediaBox/MediaResource/Fetch/LocalFileReference, image/file constructors/references, ManagedAutoremove, локальный/удалённый consumption, SecretMediaPreviewController, OpenChatMessage/Gallery и MessageHistoryEntry pin.

Хранилище аккаунта nagramix-message-media: полные UUID.bin + атомарный index.json, проверка UUID/regular-file/размера, backup exclusion. resourceData.complete + offset=0 → copyItem без многогигабайтного Data; keepResource/fetchedMediaResource, максимум два transfer, temporary/primary priority, три попытки с backoff без постоянного polling. Utility Queue сериализует записи/transfer, Atomic снимки доступны рендерингу/cache-purge. Владельцы дедуплицируют ресурс; обычный владелец не блокируется child OFF. Parent OFF/фон отменяют архивные запросы, child OFF — только временные; копии сохраняются. Резервации до force-purge, tickets/pendingClear и identity-check callbacks защищают очистку. Явная очистка/локальное удаление освобождают файлы и playback-кэш архивных LocalFileReference ID.

NagramiXMessageArchive: optional temporary совместим со старым JSON, рекурсивно собираются главные ресурсы/repr/previews/thumbnails/cover/alternatives. При рендеринге полный файл заменяется permanent LocalFileReferenceMediaResource, isUniquelyReferencedTemporaryFile=false, поэтому stock fetch копирует, а не переносит архивный оригинал. Окончание копирования публикует update/stableVersion для живого чата. Серверное удаление помечает уже одобренную запись даже после OFF. Incoming Cloud архивируются при parent ON; временные требуют child ON. Сохраняются прежние исключения secret/paid/protected-peer/обычный CopyProtected/bot-ephemeral/codes/outgoing; CopyProtected самого временного вложения разрешён только child ON. Недоступные/не полученные байты и загрузку при системной приостановке iOS обещать нельзя.

apply_archived_media_resources: старт после Account fetch callbacks; защита pending ресурсов GlobalIds/диапазона и пометка диапазона; capture до локального consumed/ManagedAutoremove/remote expired replacement; optional archive parameter и два remote callsite; standalone только у архивного snapshot в OpenChatMessageParams; expired history-entry заменяется локальной копией с сохранёнными read/location/month/attributes без второго ID; контекстное меню наблюдает существование архивной записи. Capture не вызывает read/consume; оригинал остаётся в штатном viewer/timer, локальная копия после expiry имеет обычные атрибуты.

UI: Функции/Сообщения, «Временные сообщения» после «Удалённых сообщений», key nagramix.messages.saveTemporaryMessages, initializer/current default false только при отсутствующем выборе. Native switch/info, общий поиск, RU/EN; stable IDs 103/104, прежние неизменны, comparator вставляет строки между info и label. Оба ON нужны для новых временных файлов. [Контракт](../product/SETTINGS.md), [архив](../product/features/deleted-messages.md), [временные](../product/features/temporary-messages.md).

## Проверки до нативной сборки

Новый архивный overlay применён к fresh scoped pin: 13 generated-файлов изменены, один добавлен, 266 совпадают с pending compact/hold baseline. Полное обратное исключение 12 вставок восстанавливает семь штатных файлов побайтно. 36 missing/duplicate/already-patched случаев и repeat overlay отклоняются. 11 Swift-файлов разбираются без ошибок; AccountStateManagementUtils имеет ту же старую tree-sitter ошибку на upstream-пустом `;` строки 1135, новых нет. Python, старые defaults/keys/IDs, новые RU/EN keys, ограниченность старых строк, metadata/diff проходят. Эти проверки статические и не заменяют исполнение MediaBox/UIKit/UserDefaults. Дополнительно новая нативная ARM64-компиляция №77 прошла успешно: compact/hold/archive/temporary и изменённый общий edit_history — compile_passed/device_pending.

Временные данные не коммитить: /tmp/nagramix-archive-upstream, /tmp/nagramix-telegram-pin-tree.json, /tmp/nagramix-archive-overlay-before, /tmp/nagramix-archive-media-baseline, /tmp/nagramix-media-current, /tmp/nagramix-check-archive-media.py. Scoped подготовке дополнительно нужны raw ManagedAutoremoveMessageOperations.swift и MarkMessageContentAsConsumedInteractively.swift перед apply_features. Compact/hold сохранность подтверждена совпадающими файлами; старые checkers предполагали прежнюю область.

## Защищённые функции

Русский первый язык/полные подписи, System/.nightAccent только при отсутствии preferences, stock темы/шрифты/палитры, RGB24/ARGB compatibility и dark-group fallback остаются без новых правок. 28 appearance-путей защищены, точные исключения описаны в [THEME_AUDIT.md](THEME_AUDIT.md). Прокси/DNS, камера/отмена первого кружка, истории/approval/seen-state, широкие посты/альбомы, ID/дата/взаимный контакт, вкладки/спонсор, пересылка и выбор автора не менять. Существующие сохранённые ключи и выбор не сбрасывать. Пользовательские статусы устройства не заменять успехом компиляции.

## Результат выпуска и следующий шаг

[Чистая №77](https://github.com/Mr-EFES/NagramiX/actions/runs/37766142058), run 37766142058, завершена success: build и публикация. Source и тег v0.4.7 — bcfdff03c15265462e18b0899673ea460192d3ba. Артефакт 11549025847, NagramiX-0.4.7-unsigned-arm64. [Релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.7) опубликован, isDraft=false/isPrerelease=true; русская аннотация совпадает с product/releases/0.4.7.md. Stable/latest 0.4.5 сохранён.

Скачаны именно опубликованные IPA, BUILD-PROVENANCE.txt и SHA256SUMS в outputs/0.4.7 (ignored). Новый файл 73960311 байт, версия 0.4.7/build 77, SHA256 cacafc57348cc75e4d24b1ebc80425735bb4f2ac3d0dd5608844c9b26ab7212a. validate_unsigned_ipa подтвердил ARM64/RU/bundle metadata/отсутствие временных профилей и каталогов подписи/checksum/source/upstream. Дополнительно проверены CRC всего ZIP, Workflow run provenance, 46 полных русских названий и новые temporary строки; RU 14843/198. В полном логе нет Swift compiler errors и предупреждений в NagramiX или затронутых stock Swift-файлах. Инфраструктурные уведомления Actions о Node.js/Ubuntu/очередях macOS не мешают успеху. [Полный отчёт](RELEASE_STATUS.md).

Первая попытка №76 failed в captureTemporaryBeforeViewing: message.peers — SimpleDictionary, makeRecord принимает [PeerId: Peer]. Исправлено штатным reduce-преобразованием; проверки повторно прошли, №77 скомпилировал исправление. Неуспешная попытка IPA/релиз не создавала. Логи /tmp/nagramix-0.4.7-build76-failed.log и /tmp/nagramix-0.4.7-build77.log не коммитить. Тег сборки не переносить на последующий отчётный коммит.

Следующий шаг — физическая проверка опубликованного build 77 пользователем. [План iPhone](IPHONE_TEST_0.4.7.md): все типы incoming → удаление → stock-cache clear → авиарежим/перезапуск → копия; temporary/view-once/четыре сочетания, OFF после сохранения, clear во время fetch, сеть/фон/нехватка места, old JSON/обновление; compact по референсу и hold/avatar/folder/stock OFF. Временные сообщения default OFF, для новых временных файлов нужны ON обоих пунктов. Реальные загрузки, жесты и таймеры не объявлять проверенными по одному успеху компиляции. Новый IPA без новой команды не собирать.
