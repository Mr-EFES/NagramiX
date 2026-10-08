# Тестовая сборка NagramiX 0.4.7

**Сборка и публикация завершены успешно.** Новый unsigned ARM64 IPA готов для проверки на iPhone 17 Pro Max / iOS 27.0 через SideStore с внешней подписью.

- [Скачать IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.4.7/NagramiX-0.4.7-unsigned.ipa).
- [Тестовый релиз с русской аннотацией](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.7), не черновик; prerelease.
- [Чистая сборка №77](https://github.com/Mr-EFES/NagramiX/actions/runs/37766142058), run ID 37766142058: build и публикация — success.
- Исходный коммит и тег v0.4.7: `bcfdff03c15265462e18b0899673ea460192d3ba`.
- База: Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`; проверка перед сборкой — CURRENT.
- Артефакт Actions: `11549025847`, `NagramiX-0.4.7-unsigned-arm64`.
- IPA: `NagramiX-0.4.7-unsigned.ipa`, **73 960 311 байт**, версия 0.4.7, внутренний build **77**.
- SHA256: `cacafc57348cc75e4d24b1ebc80425735bb4f2ac3d0dd5608844c9b26ab7212a`.

В релиз загружены IPA, BUILD-PROVENANCE.txt и SHA256SUMS. Именно эти опубликованные файлы скачаны в локальный outputs/0.4.7 и повторно проверены scripts/validate_unsigned_ipa.py: версия/build/bundle ID/название/RU, ARM64 Mach-O, отсутствие временных профилей и каталогов подписи, checksum и source/upstream provenance. Дополнительно прошли CRC всего ZIP, привязка к run №77, 46 полных русских названий и новые RU строки «Временных сообщений». Основной RU ресурс содержит 14843 строки, ресурс NagramiX — 198. Текст аннотации совпадает с product/releases/0.4.7.md; тег указывает на исходный коммит сборки, а не на последующий отчёт.

Включены:

- плотность компактного списка: аватар/текст/строки/отступы; default OFF;
- удержание аватарки для штатного предпросмотра и остальной строки для меню; свайпы — папки;
- отдельный архив полных файлов входящих медиа, штатное открытие копий и очистка с отменой загрузок;
- «Временные сообщения» после «Удалённых сообщений», default OFF; для новых временных/одноразовых вложений нужны ON обоих пунктов.

Статические проверки overlay/обратного diff/36 отрицательных anchors/Swift-разбора/defaults/IDs/RU/EN/метаданных пройдены. Новые compact/hold/archive/temporary и общий edit_history получили compile_passed; физические сценарии остаются device_pending. В журнале успешной сборки нет Swift compiler errors и предупреждений в NagramiX Swift-файлах или затронутых stock Swift-файлах. Actions сообщает только инфраструктурные уведомления о версиях Node.js/Ubuntu и очередях macOS; сборке и публикации они не помешали.

Первая попытка №76 остановилась на передаче SimpleDictionary как Swift Dictionary в captureTemporaryBeforeViewing. Исправлено штатным reduce-преобразованием; №77 — новая чистая компиляция с исправлением. Неуспешная попытка IPA/релиз не создавала, прежний №75 не переиздавался.

Физическая проверка ещё не выполнена. [План проверки](IPHONE_TEST_0.4.7.md), [аннотация](../product/releases/0.4.7.md), [архив](../product/features/deleted-messages.md). Стабильный latest 0.4.5 сохранён; прежние релизы и файлы не удалялись.
