# Текущий контекст NagramiX 0.4.5

Обновлено 2026-10-07. Ветка main, upstream origin/main. База — официальный Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`. Проект overlay. Новые отчёты/коммиты/аннотации — русские.

## Релиз и очистка завершены

Пользователь назначил 0.4.5 первой стабильной базой. [Релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.5) опубликован stable/latest с краткой русской аннотацией. Нативная сборка №73 успешна, [публикация №74](https://github.com/Mr-EFES/NagramiX/actions/runs/37655755680) успешна без новой компиляции. Source/tag SHA `1c85d9a8fa83edcdbaf5ebc59e9e06a8f50d1051`; последующая документация main имеет другой SHA.

Все три публичных файла скачаны и проверены: IPA version 0.4.5/build 73, ARM64, RU 14843/183, 73 897 507 байт, SHA256 `26ca404ee21b5eb7bb14070844d27033cab791567f2cdd76a1b618aa5a5a2454`. scripts/validate_unsigned_ipa.py подтверждает версию/build/source/pin/checksum/provenance и отсутствие временных подписей/профилей. В изменённых Swift-файлах compiler errors/warnings нет. Физические тесты нового исправления ещё не проведены.

Удалены старый релиз/его файлы, шесть прежних тегов и девять устаревших runs/артефактов. Одна ветка main, один workflow, один релиз/тег 0.4.5, открытых PR нет. Сборка №73 и публикация №74 одной актуальной версии сохранены как доказательства. Git-история и работающие функции сохранены. Попытка обновить поле About вернула403 Resource not accessible by integration (администрирование repo); поле не изменено. На релиз/код это не влияет.

Прямой upload из Codex получал 401, но публикация успешно завершена служебным GITHUB_TOKEN Actions. Обновление секретов для этого релиза больше не требуется. Единственный workflow поддерживает artifact_run_id: пусто — обычная новая сборка, указан id — только публикация готового IPA. Проверяются main/исходный workflow/build-success/source SHA/build-number/provenance и IPA. Продолжить можно только пустой draft с тем же target SHA; непустой/опубликованный релиз не заменяется. Не запускать новые сборки/публикации без отдельной команды пользователя.

## Исправление выбора автора

- Новый `ios/Sources/TelegramCore/NagramiXAuthorSelection.swift`: личный cloud-диалог — последовательные страницы messages.getHistory, группы/каналы — messages.search с fromId и native thread/saved-dialog параметрами; прежняя группа мигрировавшей супергруппы также проходится. Страницы по 100, общего лимита нет. Истинный StoreMessage.authorId/peer/thread проверяется. StoreMessage/AccumulatedPeers/updatePeers/transaction.addMessages(location: .Random) сохраняют найденные сообщения в Postbox до передачи ID native панели. Финальные ID повторно сверяются с базой. Медиафайлы не скачиваются.
- Сетевые ошибки/FloodWait/таймаут30s и отсутствие прогресса offset не превращаются в пустой успех. Частичный выбор при ошибке не применяется. Cloud peer недоступен — явный неуспех; серверный обход истории secret chats не реализован.
- `ios/apply_features.py` копирует helper в glob TelegramCore и подключает callback. Сохранены MetaDisposable/generation/peer/thread guards, voice-discard gate, loading dispose/main queue и прежнее объединение локального архива. Новый marker набора автора нужен только для понятного объяснения запрета native удаления. При наличии deleteLocally/deleteGlobally deletion/bans/undo остаются native. При реальном запрете — объяснение с OK и отдельным действием кэша. Ручной выбор/удаление не меняются.
- PresentationStrings и RU/EN: 3 строки пустого выбора, неуспеха и запрета удаления. Настройки/defaults/другие функции не менялись. Права Telegram не обходятся: личный чат — доступные «у меня» / «у обоих», чужие супергруппы — с deleteAllMessages.

## Проверено перед сборкой

Baseline и новый apply_features применены к чистым validation копиям точного pin. Generated diff — 6 ожидаемых файлов (helper, два controller файла, accessor и RU/EN); остальные 211 файлов проверочного дерева совпадают. Stock appearance guards проходят. Swift tree-sitter syntax четырёх файлов, Python syntax, RU intro13, metadata и diff check пройдены. Ровно 3 новых ключа на язык, прежние строки сохранены: RU183, EN109. Реальные SwiftSignalKit/API подписи и Bazel glob сверены с pin. Это статические проверки, не native compile/typecheck.

Registry select_from_author: compile_passed/device_pending, остальные функции не менялись. Native ARM64 build №73 прошёл: source `1c85d9a8fa83edcdbaf5ebc59e9e06a8f50d1051`, [run](https://github.com/Mr-EFES/NagramiX/actions/runs/37632252812),5865actions. В изменённых Swift-файлах errors/warnings нет. IPA проверен scripts/validate_unsigned_ipa.py: version0.4.5/build73/source/pin, ARM64, RU14843/183, checksum/provenance, без подписей/профилей;73 897 507байт, SHA256 `26ca404ee21b5eb7bb14070844d27033cab791567f2cdd76a1b618aa5a5a2454`. Кеш restore timeout/save warnings и Node20 deprecation — инфраструктурные предупреждения; сборка успешна. Физической проверки новой функции нет.

## Сохранённый функционал

Только выбор автора и связанное объяснение удаления изменены. Русский bundled fallback/авторизация/ручной язык, System/Dark clean-install seed (guard отсутствующего entry), stock темы/палитры/шрифты и RGB24/ARGB compatibility — прежние. Не менять их в этой задаче.

Прежние категории/поиск NagramiX используют navigationBar.primaryTextColor/navigationSearchBar; геометрия full-width48/r24/y12/item71, header ЗВОНКИ stableId49. Взаимный контакт — реальный mutualContact, текст ⇄ Взаимный контакт/native labeled item11002. Stories — completed качественный preview/blur.dark0.5/dim0.18, прежний approval/seen gate. Первый задний кружок — новое удержание после permissions, pending cancel/dismiss. Прокси — single phase15/30/60, fresh ping, online отдельно, bounded probes/background pause. Архив — local copy/edit/reply quote/select/delete, не восстановление server edit/pin, медиа требуют кэша. Wide posts/mosaic, profileID/дата, tabs/sponsor, forward/copy, defaults19 сохраняются. Timer iOS background не гарантирован; secret archive не поддерживается.

## Следующий шаг

Установить опубликованный IPA 0.4.5 №73 через SideStore на iPhone 17 Pro Max / iOS 27.0. По [плану](IPHONE_TEST_0.4.5.md) проверить обе стороны личного чата, группы с правами/без, 300+, старые сообщения, отмену/ошибки/смену чата, пересылку/жалобу, удаление только выбранных сообщений и регресс остальных функций. Stable назначен пользователем; физические результаты не объявлять полученными. [Статус релиза](RELEASE_STATUS.md).
