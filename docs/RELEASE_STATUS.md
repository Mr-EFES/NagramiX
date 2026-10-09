# Сборка NagramiX 0.4.9 для iPhone

Пользователь разрешил чистую ARM64-сборку и тестовый релиз на Telegram13.0. Русская [аннотация возможностей](../product/releases/0.4.9.md) подготовлена. [Сборка №81](https://github.com/Mr-EFES/NagramiX/actions/runs/37940157721) завершилась ошибкой компиляции двух custom элементов SettingsUI из-за нового ListViewItem API. Публикация пропущена, новый IPA отсутствует.

Сигнатуры поиска и процентного ползунка адаптированы к native neighbors/descriptors/facets; поведение и размеры сохранены. Fresh strict overlay, синтаксис двух Swift-файлов и точное совпадение методов с закреплённым протоколом проходят. Повторная чистая сборка подготовлена; успех пока не подтверждён.

- Telegram-iOS13.0, pin f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838; CURRENT на запуске №81. Минимальная iOS15.0.
- [Миграция](TELEGRAM_13_MIGRATION.md): strict overlay и брендинг проходят, 330 raw reference blobs проверены; все предыдущие функциональные правки сохранены.
- Повторить clean_build=true, artifact_run_id пустой, publish_release=true, prerelease=true из нового исходного SHA.
- Изменённые функции compile_pending/device_pending до успешного native build.

После сборки независимо проверить source/run/tag, номер и версию, ARM64, отсутствие установочных профилей/каталогов подписей, checksum/provenance, ZIP, локализации и опубликованную аннотацию. Физические сценарии — [план iPhone](IPHONE_TEST_0.4.9.md). Прежние релизы сохраняются. №80 отменён до публикации для изоляции cloned tabs helper; прежний IPA не переиздавался.
