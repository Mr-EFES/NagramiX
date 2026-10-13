# NagramiX 0.5.4: подготовка чистой сборки

Пользователь разрешил новый рабочий выпуск для физического iPhone. Чистая ARM64-сборка и публикация тестового релиза готовятся; готового IPA0.5.4 пока нет. Telegram13.0 pin f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838 проверен CURRENT.

Параметры: clean_build=true, publish_release=true, prerelease=true, artifact_run_id пустой. Сборка должна использовать все подготовленные изменения и [русскую аннотацию](../product/releases/0.5.4.md). Run/build/source SHA будут записаны после dispatch; checksum и проверка пакета — после успеха.

Правки после предыдущего build86: свайпы настроек, архивная одиночная пересылка/рассылка/Save, proxy preference sync и DNS Telegram, onboarding, skip call rating, [аудит стабильности](STABILITY_AUDIT.md). compile_pending/device_pending до новой проверки.

Повторные попытки сохраняют0.5.4; следующий рабочий выпуск0.5.5. Предыдущие releases/tags/assets сохранены. Отдельный установленный IPA прошлой версии не является результатом этой сборки. [План теста](IPHONE_TEST_0.5.4.md).
