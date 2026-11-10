# Выпуск NagramiX 0.9.2

**Выпуск 0.9.2/build193 завершён: native_compile_passed / package_verified / owner_published / device_pending.** Обычный latest [релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.9.2) опубликован 10 ноября 2026 года в 04:04:25 UTC от Mr-EFES. [IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.9.2/NagramiX-0.9.2-unsigned.ipa), [успешная сборка](https://github.com/Mr-EFES/NagramiX/actions/runs/42732784627), [проверка публикации](RELEASE_092_PUBLICATION_CHECKS.json). Source и tag v0.9.2: `67090143af03c3d709b4283f2a4b037e61e87014`, Telegram13.2/Xcode27.1. Чистая SDK-компиляция 01:11:05–02:41:58 UTC и оба задания Actions успешны. Ошибка порядка аргументов SettingsUI из №192 устранена; полный конструктор проверяется до SDK.

IPA: 93 892 619 байт, SHA256 `727ea808a237243f22672ebba46de1441b7a3ca847aa764a1f48c09a5e84c81e`. Исходный ZIP artifact13730846722 сохранён без перепаковки; его SHA256 совпал с Actions. Локально и в owner publisher проверены пакет, происхождение и checksum; API подтвердил latest, tag/source и автора/uploader всех трёх файлов Mr-EFES. Пакет неподписанный, iOS15+/ARM64; 71 ресурсный каталог по635ключей не является заявлением о числе официальных языков Telegram. README, аннотация и прежние опубликованные файлы сохранены.

Все реализованные функции имеют compile_passed; физическая проверка на iPhone остаётся device_pending. Команда на выпуск выполнена. Следующий новый выпуск — 0.9.3, только по новой личной команде; документационный commit после сборки не меняет тег/IPA и не разрешает SDK-повтор. Видимость репозитория владелец возвращает вручную через settings#danger-zone → Make private. Ниже — история подготовки; прежние pending/разрешения не заменяют этот итог.

Владелец разрешил чистую сборку IPA, исправление ошибок и повторы до успешной обычной публикации в репозитории. Источник подготовки — main после `639d57a79d6cc6d6983b8f73de80e782c5ad6d58`; все26 поздних стадий, включая явное открытие временного медиа. Следующий новый выпуск после успеха потребует новой команды.

Авторизация Mr-EFES и public проверены. Официальная база Telegram13.2, pin `24638bc69bd083981b178dd1e7f921eebbf7fc46`, актуальна; iOS15+, ARM64, Xcode27.1. README и старые опубликованные материалы сохраняются.

Статус: source_preflight_passed; SDK/пакет/публикация pending. [Проверки](RELEASE_092_PREFLIGHT_CHECKS.json):504Swift parse,50migration refusals,14historical runtime исполнений,103inverse refusals,725paths, full7321/canonical224 member audit,71×635/45254lookup на режим,28owner и32synthetic package tests. SHA предыдущих целевых тестов и всех26стадий подтверждены; прикладных изменений после проверенного639d57a нет. Подготовка метаданных не означает успешной SDK-компиляции. Команда запуска после проверок: workflow_dispatch, main, artifact_run_id пусто, clean_build=true, publish_release=true, prerelease=false. Публикация — только через проверку исходного Actions ZIP/IPA и owner publisher.

Журналы и состояние текущего процесса: `/tmp/nagramix-release-092/`. Физическая приёмка на iPhone остаётся отдельным шагом после IPA.

## Изменение режима проверок по команде владельца

№191 [run42718697198](https://github.com/Mr-EFES/NagramiX/actions/runs/42718697198), source`accd1f41df9845de92d7fc8116b459aeaa7f8362`, дошёл до применения overlay и остановлен по новой команде ускорить Apple Swift checks. Это отмена, а не зафиксированная ошибка исходников. [Новый режим](PATCH_VALIDATION_MODE.md): повторные исторические тесты необязательны, настоящие проверки кода/SDK/IPA сохранены. Следующий dispatch остаётся0.9.2, extended_patch_tests=false, clean_build=true, publish_release=true, prerelease=false.

## SDK192 и проверенный повтор

[№192](https://github.com/Mr-EFES/NagramiX/actions/runs/42721038519) отMr-EFES: source`0163da0b35d5bdb8f1dac4414b9d6b1901a79feb`, подготовка патчей403секунды, после успешных обязательных проверок нативная компиляция остановилась на неправильном порядке двух аргументов SettingsUI. [Исправление](RELEASE_092_SETTINGS_COMPILE.md): одна перестановка и новый обязательный compiler probe полного73-параметрового вызова до SDK. Повторяется та же0.9.2 в чистом режиме до успешного IPA и owner publication; неудачный192 не публикуется.
