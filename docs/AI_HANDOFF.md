# Текущий контекст NagramiX 0.4.5

Обновлено 2026-10-07. Ветка main, upstream origin/main. База — официальный Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`. Проект overlay. Новые отчёты/коммиты/аннотации — русские.

## Текущая задача — разрешённая сборка и публикация

Пользователь положительно оценил предыдущий установленный IPA, кроме выбора/удаления автора. После анализа разрешил исправить только эту функцию; теперь дал отдельную команду собрать 0.4.5 для физического iPhone и опубликовать релиз с краткой русской аннотацией. Запуск этой сборки разрешён. Устройство iPhone 17 Pro Max, iOS 27.0, SideStore. IPA №73 собран и проверен; создан черновик релиза, загрузка assets пока блокирована401. Стабильность до физической приёмки не заявлять.

## Исправление выбора автора

- Новый `ios/Sources/TelegramCore/NagramiXAuthorSelection.swift`: личный cloud-диалог — последовательные страницы messages.getHistory, группы/каналы — messages.search с fromId и native thread/saved-dialog параметрами; прежняя группа мигрировавшей супергруппы также проходится. Страницы по 100, общего лимита нет. Истинный StoreMessage.authorId/peer/thread проверяется. StoreMessage/AccumulatedPeers/updatePeers/transaction.addMessages(location: .Random) сохраняют найденные сообщения в Postbox до передачи ID native панели. Финальные ID повторно сверяются с базой. Медиафайлы не скачиваются.
- Сетевые ошибки/FloodWait/таймаут30s и отсутствие прогресса offset не превращаются в пустой успех. Частичный выбор при ошибке не применяется. Cloud peer недоступен — явный неуспех; серверный обход истории secret chats не реализован.
- `ios/apply_features.py` копирует helper в glob TelegramCore и подключает callback. Сохранены MetaDisposable/generation/peer/thread guards, voice-discard gate, loading dispose/main queue и прежнее объединение локального архива. Новый marker набора автора нужен только для понятного объяснения запрета native удаления. При наличии deleteLocally/deleteGlobally deletion/bans/undo остаются native. При реальном запрете — объяснение с OK и отдельным действием кэша. Ручной выбор/удаление не меняются.
- PresentationStrings и RU/EN: 3 строки пустого выбора, неуспеха и запрета удаления. Настройки/defaults/другие функции не менялись. Права Telegram не обходятся: личный чат — доступные «у меня» / «у обоих», чужие супергруппы — с deleteAllMessages.

## Проверено перед сборкой

Baseline и новый apply_features применены к чистым validation копиям точного pin. Generated diff — 6 ожидаемых файлов (helper, два controller файла, accessor и RU/EN); остальные 211 файлов проверочного дерева совпадают. Stock appearance guards проходят. Swift tree-sitter syntax четырёх файлов, Python syntax, RU intro13, metadata и diff check пройдены. Ровно 3 новых ключа на язык, прежние строки сохранены: RU183, EN109. Реальные SwiftSignalKit/API подписи и Bazel glob сверены с pin. Это статические проверки, не native compile/typecheck.

Registry select_from_author: compile_passed/device_pending, остальные функции не менялись. Native ARM64 build №73 прошёл: source `1c85d9a8fa83edcdbaf5ebc59e9e06a8f50d1051`, [run](https://github.com/Mr-EFES/NagramiX/actions/runs/37632252812),5865actions. В изменённых Swift-файлах errors/warnings нет. IPA проверен scripts/validate_unsigned_ipa.py: version0.4.5/build73/source/pin, ARM64, RU14843/183, checksum/provenance, без подписей/профилей;73 897 507байт, SHA256 `26ca404ee21b5eb7bb14070844d27033cab791567f2cdd76a1b618aa5a5a2454`. Кеш restore timeout/save warnings и Node20 deprecation — инфраструктурные предупреждения; сборка успешна. Физической проверки новой функции нет.

## Версия и публикация

Версия workflow/registry, README, единственная аннотация product/releases/0.4.5.md, docs и план IPHONE_TEST_0.4.5.md актуализированы. Сохранить один существующий workflow. Native build на macOS/Xcode с корректным Bazel content cache; версия/source/build/RU/ARM64/checksum/provenance и отсутствие временных подписей проверяются до публикации scripts/validate_unsigned_ipa.py. Публиковать prerelease для физической приёмки. Предыдущие GitHub теги/файлы релизов не перезаписывать. Общий run73 failure после успешного build: release job не появился; failed-job rerun HTTP500, GitHub status сообщает инцидент Actions/Git. Собственный draft v0.4.5 создан через gh API: release405895197, target1c85d9a, аннотация из product/releases/0.4.5.md. Assets0: upload возвращает401 Bad credentials, при рабочем api.github.com/gh auth status. Пользователю отправлен запрос обновить GH_TOKEN в секретах окружения, только этот repo/Contents Read-write. Не просить секрет в чат, не публиковать пустой draft, не пересобирать готовый IPA. Локально /tmp/nagramix-release045 содержит3проверенных файла (в другой среде скачатьartifact11491604794 изrun73). После обновления доступа загрузить без clobber, publish prerelease/latest=false, проверить публичный download, tag/source и body. Документация main может иметь последующий SHA, tag обязан остаться на build-source.

## Сохранённый функционал

Только выбор автора и связанное объяснение удаления изменены. Русский bundled fallback/авторизация/ручной язык, System/Dark clean-install seed (guard отсутствующего entry), stock темы/палитры/шрифты и RGB24/ARGB compatibility — прежние. Не менять их в этой задаче.

Прежние категории/поиск NagramiX используют navigationBar.primaryTextColor/navigationSearchBar; геометрия full-width48/r24/y12/item71, header ЗВОНКИ stableId49. Взаимный контакт — реальный mutualContact, текст ⇄ Взаимный контакт/native labeled item11002. Stories — completed качественный preview/blur.dark0.5/dim0.18, прежний approval/seen gate. Первый задний кружок — новое удержание после permissions, pending cancel/dismiss. Прокси — single phase15/30/60, fresh ping, online отдельно, bounded probes/background pause. Архив — local copy/edit/reply quote/select/delete, не восстановление server edit/pin, медиа требуют кэша. Wide posts/mosaic, profileID/дата, tabs/sponsor, forward/copy, defaults19 сохраняются. Timer iOS background не гарантирован; secret archive не поддерживается.

## Следующий шаг

Завершить загрузку файлов/публикацию уже проверенного IPA0.4.5№73 после обновления доступа uploads.github.com; повторно проверить публичный IPA и tag. Затем физическая приёмка выбора автора (входящие/исходящие, группы с правами/без, 300+, старые сообщения, отмена/ошибка/смена чата, пересылка/жалоба, невыбранные сообщения) и общий регресс сохранённых функций по [плану](IPHONE_TEST_0.4.5.md). Анализ — [AUTHOR_SELECTION_AUDIT.md](AUTHOR_SELECTION_AUDIT.md), статус — [PENDING_RELEASE.md](PENDING_RELEASE.md). Не заявлять без физической проверки, что новая версия стабильна.
