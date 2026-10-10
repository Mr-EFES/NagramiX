# NagramiX 0.5.1: подготовка чистой сборки

Пользователь разрешил новую тестовую ARM64-сборку для физического iPhone с релизом в репозитории. В выпуск входят все подготовленные изменения после предыдущей успешной сборки №83. Прежние релизы, теги и файлы сохраняются.

Официальная база повторно проверена: Telegram-iOS 13.0, `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`, CURRENT, minimum iOS15.0. Workflow — `.github/workflows/build-unsigned-ipa.yml`, macOS26/Xcode26.6, release_arm64. Планируются clean_build=true, publish_release=true, prerelease=true, пустой artifact_run_id. Восстановление/сохранение кеша пропускаются.

Новый исходный SHA и run будут записаны после commit/dispatch. Новый IPA пока не получен и не опубликован. Подготовленные функции compile_pending/device_pending. Физическая проверка ещё не выполнена.

[Аннотация по функциям](../product/releases/0.5.1.md) · [Приёмка на iPhone](IPHONE_TEST_0.5.1.md).
