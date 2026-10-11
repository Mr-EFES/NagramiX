# NagramiX 0.5.3: проверенный IPA опубликован

Чистая нативная сборка и публикация тестового релиза завершились успешно. Опубликованный IPA скачан и независимо проверен. Все накопленные функции включены; физическая приёмка на iPhone ожидается.

| Параметр | Результат |
| --- | --- |
| Версия / build | 0.5.3 / 86 |
| База | Telegram-iOS13.0, `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838` |
| Workflow | [№86](https://github.com/Mr-EFES/NagramiX/actions/runs/38176187919): build и release success |
| Релиз | [v0.5.3](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.3), prerelease, не draft |
| IPA | [NagramiX-0.5.3-unsigned.ipa](https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.3/NagramiX-0.5.3-unsigned.ipa) |
| Исходный SHA / tag target | `8c0c117647ae26c444965689773f1ae77a151f99` |
| Размер | 80 924 082 байта |
| SHA256 | `8c5028bfb13cbdb1ab1c12449b714901db13eee60fb398504048c59bf3581844` |
| Совместимость | ARM64, iOS15.0+, внешняя подпись, например SideStore |
| Входные параметры | clean_build=true, publish_release=true, prerelease=true; artifact_run_id пустой |

Проверка опубликованного пакета: checksum и BUILD-PROVENANCE совпадают с исходным SHA, pin и workflow; ZIP цел; bundle ID/name/version/build/RU region правильные; все6 Mach-O ARM64; background audio сохранён. Временных `_CodeSignature` и embedded profiles нет. Основной RU ресурс14863ключа, все268 RU и194 EN значений NagramiX совпадают с исходниками. Все31 встроенные мелодии совпали по SHA256. Аннотация релиза совпадает с [русскими тезисами](../product/releases/0.5.3.md).

Предыдущая попытка [№85](https://github.com/Mr-EFES/NagramiX/actions/runs/38166584585) не создала IPA из-за неверного типа weak property окна авторизации. `textAlertController(context:...)` возвращает `ViewController`; тип `nagramiXAuthorizationAlert` исправлен на `ViewController?`. Успешная нативная компиляция№86 подтверждает исправление типов. Cancel/Logout, weak ownership, локализация и защита от дублей сохранены; восстановление серверного ключа этим не заявляется.

Правило версий: повторные попытки текущего рабочего выпуска сохраняют0.5.3; следующий рабочий выпуск0.5.4. Прежние releases/tags/assets сохраняются. Более поздние commits документации не являются исходным SHA этого IPA.

Уровень проверки: compile_passed/device_pending. Компиляция и упаковка не подтверждают реальные аудиомаршруты, повторные записи, сетевую отправку, авторизацию, серверную обработку фото или жесты. Следующий шаг — установка и [физический тест](IPHONE_TEST_0.5.3.md); дополнительные сборки без новой задачи не нужны.
