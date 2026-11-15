# Итог проверки и публикации0.9.8/build219

[IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.9.8/NagramiX-0.9.8-unsigned.ipa) опубликован15ноября2026,17:38:09UTC от Mr-EFES как обычный latest [релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.9.8). [Actions219](https://github.com/Mr-EFES/NagramiX/actions/runs/43721830908): оба задания успешны. Полная ARM64/iPhoneOS SDK-компиляция прошла15:44:54–17:34:51UTC,10039действий. Это результат настоящей компиляции и проверки пакета, а не статический анализ.

Собран и помечен тегом `v0.9.8` commit `2a8d8a76fcf16db4a5eadc503ed180a9b3a4af56`. Поздний commit отчёта/registry не меняет IPA или тег. Включены существовавшие утверждённые стадии75–91 и минимальная compile-совместимость92; manifest полногоsource92 `5d66aa3f166a24239f328475603fb94cdbab2e46660b1e071f2a69c659644789`.

## Изменения подготовки

- [Полный список файлов](RELEASE_098_CHANGED_FILES.txt) относится к реально собранной ревизии относительно начала подготовки926c1fb. [Все изменения между релизами](https://github.com/Mr-EFES/NagramiX/compare/v0.9.7...v0.9.8) включают ранее согласованные функции75–91.
- Стадия92 меняет ровно2строки в `ChatTranslationPanelNode.swift` и `ChatMediaEditorScreen.swift`: использует сохранённый account context в weak-self map и разрешает существующий caption gate внутри его Swift-модуля. Тела методов и вся прочая логика сохранены;15новыхinc — неизменяемые preimage/output/guard snapshots. [Разбор](RELEASE_098_COMPILE_COMPATIBILITY.md).
- Тестовая обвязка исправлена по полным логам214–218: native Texture UIColor property, асинхронная граница animation completion, контролируемые отрицательные диагностики, разделение генерируемых Swift-деклараций, реальные CoreGraphics и weak-reference observers. Теперь actual producer/body/caller компилируются в разных файлах; оба исходных218отказа обязаны отвергаться до основной SDK.
- Workflow сохраняет все обязательные проверки и собирает независимые ранние ошибки за один проход с ненулевым итогом. Сохраняются только явно перечисленные диагностические файлы. Новые проверки не optional. [Механизм](PRE_SDK_FAILURE_COLLECTION.md).
- IPA validator для0.9.8 проверяет678ключей вместо668 с точной SHA-цепочкой стадий86/88; контракты старых0.9.6/0.9.7 не изменены. Обе аннотации0.9.7/0.9.8 сохранены. Bazel/release_arm64, Xcode27.1, закреплённый Telegram13.2 и12submodules, targets, временные профили и unsigned packaging сохранены. Зависимости не обновлялись, README/LICENSE неизменны.

## Проверки

Все10локальных глобальных проверок exact source92 прошли:109earlychecks/68fixtures/136debug–optimized запусков плюс8cross-file compiler records,677Swiftparse и native Postbox,92обратимые стадии,49исторических деревьев, strict71×678каталогов, ссылки на реальные members/строки, workflow/mode/metadata/diff. Эти локальные результаты отдельно обозначены и не выдаются за iPhoneOS SDK.

В219 повторены реальные Apple early/API checks, вся обязательная overlay/global матрица, проверка среды и cold gate. Нет автоматического push-trigger, concurrency-отмены или дублирующего dispatch. Предыдущие214–218разобраны целиком: последние218с `--keep_going` дали два первичных compiler error в разных модулях; оба исправлены до219. [Журнал](RELEASE_098_RUN.md) содержит отдельные receipts каждой попытки.

Исходный ActionsZIP97689928байт имеет SHA256 `d479c1b3048755a67c088073be09ce9d36f7f20f243e5ce8261cad3e5350ac75`, совпавший с digest GitHub; CRC и набор из3файлов проверены. [Артефакт](https://github.com/Mr-EFES/NagramiX/actions/runs/43721830908/artifacts/14172830682) доступен в Actions. IPA98125760байт, SHA256 `a09b253990fd969c4c4c00800e8b9f76868b7fbe4d5024e874a04716bd9cf24e`: version0.9.8/build219/source/provenance/checksums,6ARM64/iPhoneOS binaries для физического iPhone/iOS15+, локализации, ресурсы, шрифты/лицензии и отсутствие embedded profiles проверены.

Публикация выполнена владельцем. Независимая повторная сверка подтвердила latest, author/uploader Mr-EFES, source/tag и SHA/размер всех3assets. Все10прежних релизов,30ихassets и13tag targets сохранены. [Машиночитаемый отчёт](RELEASE_098_PUBLICATION_CHECKS.json).

## Оставшиеся проверки

Пакет неподписанный, как и прежде; для установки нужна пользовательская подпись. Сборка не подтверждает живые YouTube/PiP, звук, запись, UIKit-анимации, жесты и серверное принятие кружков на телефоне. Все80функций имеют `compile_passed`, все80остаются `device_pending`; [план iPhone](DEVICE_CHECK_098.md). Автоматически менять видимость репозитория нельзя: после скачивания владелец вручную возвращает [Make private](https://github.com/Mr-EFES/NagramiX/settings#danger-zone).
