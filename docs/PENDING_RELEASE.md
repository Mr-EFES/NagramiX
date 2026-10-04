# Сборка и физическая проверка 0.4.2

**0.4.2, build 67** собрана и [опубликована](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.2) 2026-10-04 как обычный релиз Latest. [Нативная сборка и публикация](https://github.com/Mr-EFES/NagramiX/actions/runs/37230513623) прошли успешно. Единственная ветка — `main`.

[Скачать ARM64 IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.4.2/NagramiX-0.4.2-unsigned.ipa). Для установки требуется внешняя подпись, например SideStore. Исходный SHA `8ca39b000ed98256bca37dcfe9190408720d9aa0`, база Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`.

SHA-256: `3b705d5a49d0cdd97f0b7ca06ba8d355b096d02ce9ff6acb358d8d6a1e805e2a`. Скачанный IPA проверен: версия 0.4.2/build 67, ARM64, bundle ID com.mr-efes.nagramix, русский development region, 14843 основных русских строк и 179 дополнительных строк. Временные подписи/профили отсутствуют, provenance и контрольная сумма соответствуют файлу. BUILD-PROVENANCE.txt и SHA256SUMS приложены к релизу.

Убраны дополнительные изменения темы в defaultPresentationData и фоне настроек NagramiX. Системное оформление при старте определяется по окну, русский язык — fallback интерфейса и сетевого пакета; ручной выбор сохраняется. Другие generated-файлы функций совпадают с предыдущей версией.

Пользователь подтвердил работу функций предыдущего IPA, кроме тем. Новое оформление и русский default требуют проверки на iPhone 17 Pro Max, iOS 27.0, SideStore по [плану](IPHONE_TEST_0.4.2.md). Успех нативной сборки не является результатом физической проверки этих изменений.
