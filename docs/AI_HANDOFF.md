# Контекст разработки NagramiX 1.0

Версия1.0 закреплена владельцем как исходная база доработки перед App Store. Повышать её и запускать новую сборку только по отдельной команде. Main сохраняет все изменения приложения; очистка старых выпусков не переписывает историю и не меняет runtime.

## Состояние базы

- [GitHub Release1.0](https://github.com/Mr-EFES/NagramiX/releases/tag/v1.0), latest, release449086531, опубликован17ноября2026 в20:06:33UTC. Author/uploader всех трёх файлов — Mr-EFES.
- [Actions224](https://github.com/Mr-EFES/NagramiX/actions/runs/44103614473), source/tag `4b839e78591eecd5349bfbc347aa8c61f351267a`. Оба задания SUCCESS, ARM64/iPhoneOS SDK17:17:56–19:11:18UTC,10039actions;125earlyApplechecks/102fixtures/204debug–optimized executions и mandatory source/localization/Postbox/cold прошли.
- IPA98159830bytes, SHA256 `7bce23243183cddd2d1c56b57266a7a6d96d883c436272b8b8993c7b728ee389`. Exact3original files/CI digest/CRC/provenance/71×680catalogs/iOS15+ и отсутствие embedded profiles проверены.
- Symbols artifact14360543231; UUID executable/dSYM `4AD768ED-7670-3507-8726-8E4EDC2BC619`. Оригинальный IPA artifact14360179061. Все файлы1.0, source tag и успешный run сохраняются при очистке.
- Runtime109,5943immutableinc/322plans, manifest `088cc2f3cf617be451b539fdcb691cae5e2719f8fab8c57167384fde72c4eca1`,37696source file entries/26symlinks. Последняя сгенерированная полная база была `/tmp/nagramix-file-caption109/source`; если временный каталог отсутствует, воспроизвести через штатный overlay, не подменять pin. Telegram13.2/pin24638bc69bd083981b178dd1e7f921eebbf7fc46.
- Registry80compile_passed, все80device_pending. [Итог](RELEASE_100_FINAL_CHECKS.md), [receipt](RELEASE_100_PUBLICATION_CHECKS.json), [план iPhone](DEVICE_CHECK_100.md).

## Последние изменения приложения

105: WebKit/PiP callback lifetime и работа на main queue;106: скрытие/перестройка вкладок и стабильная геометрия пустых звонков;107: независимый профиль галерейных кружков и native reader/export;108: горизонтальный выбор качества при любом шрифте;109: согласованный ведущий LF в file-caption для обоих редакторов, отправки и edit, без накопления строк и с корректным сдвигом entities. Эти изменения включены в IPA224.

Новые исправления оформлять runtime110+ только при необходимости; прежние guards/anchors/SHA и immutable файлы не переписывать. Ранние version-named модули и compiler fixtures — зависимости1.0, а не отдельные распространяемые версии. Особые правила и контрактные ограничения — в [AGENTS](../AGENTS.md), настройки — в [SETTINGS](../product/SETTINGS.md), функции — в [реестре](../product/features/registry.json).

## Следующий этап

Владелец закрепил1.0 и разрешил разовую очистку всех других опубликованных версий, старых тегов/результатов сборок и материалов. [Сверка очистки](REPOSITORY_BASELINE_100.md). Это не разрешение на будущие автоматические удаления. Следующие изменения сразу owner commit/push main, без SDK до новой команды; тегv1.0 остаётся на фактическом SDK-source.

Текущая IPA unsigned/build-only. До App Store остаются физическая приёмка, конфигурация Distribution/AppStoreConnect и проверка требований магазина. Готовность к модерации не подтверждена. Не обещать универсальный обход серверных/DRM ограничений YouTube; живое воспроизведение и PiP проверять отдельно. Альбомный редактор и постоянное фоновое удержание не реализованы, бесплатная подпись не добавляет APNs.

Публикация1.0 уже завершена после подтверждённого официального GitHubCLI device flow, без новой SDK. Не повторять поиск старых credential-профилей и не читать токены. Истёкший вход восстанавливать только официальным способом. Видимость меняет владелец вручную.
