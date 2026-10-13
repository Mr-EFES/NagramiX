# NagramiX 0.5.4: повторная сборка после исправления ресурсов

Пользователь разрешил новый рабочий выпуск для физического iPhone. Чистая ARM64-сборка№87 выполняется; тестовый релиз будет опубликован после успеха; готового IPA0.5.4 пока нет. Telegram13.0 pin f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838 проверен CURRENT.

Параметры: clean_build=true, publish_release=true, prerelease=true, artifact_run_id пустой. Сборка должна использовать все подготовленные изменения и [русскую аннотацию](../product/releases/0.5.4.md). Workflow: [№87](https://github.com/Mr-EFES/NagramiX/actions/runs/38393039193), run_id=38393039193, source SHA `41ee545ece66514d340e641fba183fd848a47149`; checksum и проверка пакета — после успеха.

Правки после предыдущего build86: свайпы настроек, архивная одиночная пересылка/рассылка/Save, proxy preference sync и DNS Telegram, onboarding, skip call rating, [аудит стабильности](STABILITY_AUDIT.md). compile_pending/device_pending до новой проверки.

Повторные попытки сохраняют0.5.4; следующий рабочий выпуск0.5.5. Предыдущие releases/tags/assets сохранены. Отдельный установленный IPA прошлой версии не является результатом этой сборки. [План теста](IPHONE_TEST_0.5.4.md).

Попытка[№87](https://github.com/Mr-EFES/NagramiX/actions/runs/38393039193) завершилась до компиляции: Bazel обнаружил одинаковые bundle paths новых PNG одновременно в AppResources/Lib.data и ios_application.resources. Удалён второй владелец; штатный AppResources сохранён, assets/manifest/loader прежние. Версия остаётся0.5.4, нового IPA ещё нет.
