# Сборка NagramiX 0.4.9 для iPhone

Пользователь разрешил новую чистую ARM64-сборку и тестовый релиз на актуальной базе Telegram 13.0. Исходники и русская [аннотация возможностей](../product/releases/0.4.9.md) подготовлены. Нативная сборка готовится; новый IPA пока не опубликован.

- Telegram-iOS:13.0, pin f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838; проверка перед сборкой CURRENT.
- [Миграция и проверки](TELEGRAM_13_MIGRATION.md): полный строгий overlay и брендинг проходят; сетевой движок, CameraLegacy, native download pools и новые RU keys адаптированы.
- План: clean_build=true, artifact_run_id пустой, publish_release=true, prerelease=true; новый исходный SHA, предыдущий IPA не переиздавать.
- Текущие новые функции compile_pending/device_pending. Номер/исходный SHA/run фиксируются после dispatch; компиляция и публикация пока не подтверждены.

После сборки проверить фактический source SHA, номер, версию, ARM64, отсутствие временных подписей/профилей, checksum и provenance. Физические сценарии — [план iPhone](IPHONE_TEST_0.4.9.md). Предыдущие релизы сохраняются.
