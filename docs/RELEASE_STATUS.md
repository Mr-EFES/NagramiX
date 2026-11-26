# NagramiX 1.0.5

26 ноября 2026 года опубликована сборка №236 для iPhone с iOS 15 и новее. В неё вошли исправления воспроизведения видео, расшифровки удалённых сообщений и раскладки редактора круглого видео. Для установки IPA требуется подпись. [Скачать IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v1.0.5/NagramiX-1.0.5-unsigned.ipa) · [Релиз v1.0.5](https://github.com/Mr-EFES/NagramiX/releases/tag/v1.0.5)

Сборка №231 опубликована 21 ноября 2026 года для проверки на iPhone. В неё вошли исправления ползунка битрейта кружков, переходов PiP, запуска YouTube и текста предупреждения DoH, а также обновлённая история правок. Идентификатор пакета — `com.nagramix.ios`. [Релиз v1.0.3](https://github.com/Mr-EFES/NagramiX/releases/tag/v1.0.3)

## Опубликованная база 1.0

[Релиз1.0/build224](https://github.com/Mr-EFES/NagramiX/releases/tag/v1.0) опубликован и закреплён владельцем как стартовая версия подготовки к App Store. [Скачать IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v1.0/NagramiX-1.0-unsigned.ipa).

| Проверка | Результат |
| --- | --- |
| Исходники и обязательные ранние проверки | passed |
| Полная ARM64/iPhoneOS SDK-сборка224 | compile_passed |
| Состав IPA, SHA256, provenance, локализация | package_verified |
| Публикация от Mr-EFES, latest/tag/3assets | owner_published |
| Физическая приёмка80функций | device_pending |
| Distribution и App Store Connect | pending |

Source/tagv1.0: `4b839e78591eecd5349bfbc347aa8c61f351267a`. [Успешная Actions224](https://github.com/Mr-EFES/NagramiX/actions/runs/44103614473). Telegram13.2/iOS15+, runtime109. IPA98159830bytes/SHA256 `7bce23243183cddd2d1c56b57266a7a6d96d883c436272b8b8993c7b728ee389`; dSYM соответствует executable.

Включены исправления PiP/WebKit, вкладок и звонков, независимого качества/экспорта галерейных кружков, горизонтального выбора качества при любом шрифте и подписи файлов в обоих редакторах. [Подробная проверка](RELEASE_100_FINAL_CHECKS.md), [receipt](RELEASE_100_PUBLICATION_CHECKS.json).

По прямой команде владельца другие версии и устаревшие материалы удалены, сохраняя сборку1.0, зависимости и историю main. [Итог очистки](REPOSITORY_BASELINE_100.md). Версия остаётся1.0 до отдельного решения о повышении. Новая сборка этой операцией не запускается.

До модерации нужен [тест на iPhone](DEVICE_CHECK_100.md) и отдельная подготовка подписи Distribution, конфигурации магазина и App Store Connect. Опубликованная IPA неподписанная и не является готовым пакетом для App Store upload.
