# Сборка и физическая проверка 0.4.3

**NagramiX 0.4.3, build 68** собрана и [опубликована как тестовый релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.3) 2026-10-05. [Нативная сборка и публикация](https://github.com/Mr-EFES/NagramiX/actions/runs/37328777156) прошли успешно. Ветка main.

[Скачать unsigned ARM64 IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.4.3/NagramiX-0.4.3-unsigned.ipa). Для установки требуется внешняя подпись, например SideStore. Исходный SHA `371eb84e9b0c2845856dd9d6809015e8166a84bb`. Основа — Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`.

SHA-256: `de31cdbc398234aac40c9241d27e2a8cb8c0cf1fa9bb8f091d2745b1d490688f`. Размер 73 888 480 байт. Проверены metadata/version/build68, ARM64, bundle ID, русский development region, 14843 основных/179 дополнительных RU строк, полное «Изменить», отсутствие временных подписей/профилей и совпадение provenance/checksum. BUILD-PROVENANCE.txt и SHA256SUMS приложены к релизу.

Включены все накопленные правки: stock-оформление Telegram, русский после первой авторизации, лёгкий blur качественного preview истории, заголовок «Звонки» над Force TCP, согласованные defaults. Физических результатов пока нет. [Аннотация](../product/releases/0.4.3.md), [план](IPHONE_TEST_0.4.3.md). iPhone 17 Pro Max, iOS 27.0, SideStore.
