# NagramiX 0.5.7: подготовка тестового IPA

Пользователь16октября отдельно разрешил сборку для физического iPhone. Все правки после build92 и согласованные экраны включены. Native build ещё не завершён. clean_build=false, publish_release=false, prerelease=true, artifact_run_id пустой. Старые релизы/теги/IPA сохраняются.

[Изменения](../product/releases/0.5.7.md) · [Приёмка](IPHONE_TEST_0.5.7.md).

# NagramiX0.5.6: IPA build92 собран и проверен

Нативная ARM64-сборка, упаковка и загрузка артефакта завершились успешно. Пакет независимо скачан и проверен. Публикация GitHub Release не выполнялась; прежние releases/tags/assets сохранены. Физический iPhone пока не проверен.

| Параметр | Значение |
| --- | --- |
| Версия / build | 0.5.6 / 92 |
| Source SHA | f33c73cf59753ffbee044889e21c00bc8f0197cb |
| Workflow | [№92](https://github.com/Mr-EFES/NagramiX/actions/runs/38811585840), success |
| Артефакт ZIP | [NagramiX-0.5.6-unsigned-arm64](https://github.com/Mr-EFES/NagramiX/actions/runs/38811585840/artifacts/12013456168), хранится до29октября2026 |
| Параметры | clean_build=false, publish_release=false, prerelease=true, artifact_run_id пустой |
| IPA | NagramiX-0.5.6-unsigned.ipa,87793747байт |
| SHA256 IPA | 844898c01900954448ebf422dd0faf3715a090c4c9669b8825f0d1f5cca23905 |
| SHA256 ZIP | 5f4c99c5df71d91ba2c05fc2154f75fe17ad82220f60aac08ee78772f35e9718 |
| Native / пакет / iPhone | compile_passed / проверен / device_pending |

Скачивание выполнено через штатный GitHub-коннектор (CLI redirect к Azure дал403). ZIP SHA совпал с GitHub artifact digest, ZIP и IPA CRC целы. scripts/validate_unsigned_ipa.py подтвердил версию/build/source/pin/provenance/checksum, ARM64/RU/31мелодию/3PNG onboarding/отсутствие профилей. Дополнительно6Mach-OARM64, MinimumOS15.0/background audio,268RU и194ENзначений NagramiX точно совпали с исходниками, primaryNagramiX1 и alternates2…8 для iPhone/iPad. Пакет unsigned, требуется внешняя подпись тем же способом, что и прежняя установка.

Локальные доказательства `/workspace/.codex-validation-nagramix-056/artifact92`, копия для передачи `/workspace/outputs/NagramiX-0.5.6-build92-unsigned.ipa`. [Изменения](releases/0.5.6.md) · [Приёмка iPhone](IPHONE_TEST_0.5.6.md). Успех компиляции не подтверждает выполнение камеры/музыки/AVKit/доставки на устройстве.

Первая попытка91/source6038007 завершилась ошибкой Swift-порядка аргументов proxy useForCalls; IPA не был создан. Исправлениеf33c73c — одна перестановка,109вызовов проверены по pinned init;573overlay outputs,572неизменных. Push не включал запрещённый docs-onlydf09b0c: изолированный worktree от6038007, только compiler fix, fast-forward main, auto-review accepted. Этот отчёт и итоговые статусы обновлены локально; отдельный docs-only push не повторяется.

# NagramiX0.5.5: проверенный IPA опубликован

Чистая нативная ARM64-сборка, упаковка и тестовая публикация завершились успешно. Опубликованный пакет независимо скачан и проверен. Физический тест на iPhone 17 Pro Max / iOS27.0 ещё не выполнен; [изменения](releases/0.5.5.md), [приёмка](IPHONE_TEST_0.5.5.md).

| Параметр | Значение |
| --- | --- |
| Версия / build | 0.5.5 / 89 |
| Source SHA / tag target | 34bb327c9af011a7916c0bca737ae6fcdffdec9e |
| Workflow | [№89](https://github.com/Mr-EFES/NagramiX/actions/runs/38554657344), build и release success |
| Релиз | [v0.5.5](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.5), prerelease, не draft |
| IPA | [NagramiX-0.5.5-unsigned.ipa](https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.5/NagramiX-0.5.5-unsigned.ipa) |
| Размер | 85 430 772 байта |
| SHA256 | 923cbd8c468125d8f69480c8c02940dbf4f71fe32136aaf5e29bd81043f858be |
| Платформа | ARM64, iOS15.0+, bundle com.mr-efes.nagramix, RU region, background audio |
| База | Telegram13.0, f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838, CURRENT при сборке |
| Входные параметры | clean_build=true, publish_release=true, prerelease=true, artifact_run_id пустой |
| Preflight | full overlay460/460 совпал;7targeted validators,3resource tests,metadata PASS |
| Нативная компиляция / пакет / iPhone | пройдена / проверен / не проверено |

Независимая проверка `/workspace/.codex-validation-nagramix-055-build89/release`: SHA256SUMS и BUILD-PROVENANCE совпали с файлом, source SHA/pin/run; tag указывает на тот же commit; тело релиза совпало с аннотацией0.5.5. ZIP CRC цел. Все6Mach-O ARM64, minimum15.0/background audio подтверждены. Временных _CodeSignature/embedded profiles нет. Основной RU ресурс14863ключа; все265RU/191EN значения NagramiX совпали с исходниками, удалённых ProfileLink ключей нет. Все31мелодии, два onboarding PNG и26RU/EN Tour значений прошли validator.

В build89 включены first-login Postbox handoff, выбор автора/смешанное удаление, действия архивного выделения/один пункт «Избранное», шесть коротких DNS, переход к записи с музыкой, анти-капс, анонимные стикеры/скрытие заблокированных, таймер селфи3–2–1 defaultON и удаление «Подмены профиля». Native compile подтверждён; выполнение XCTest и физические вход/AVFoundation/Photos/доставка/получатель стикеров не проверялись. Все соответствующие сценарии остаются device_pending.

Пользователь явно подтвердил push/main, сборку и тестовую публикацию после отказа автоматического reviewer первой попытки. Старые releases/tags/assets операции этого выпуска не изменяли. Source SHA относится к коду IPA; последующие commits документации и статусов не меняют происхождение пакета. Следующий рабочий выпуск0.5.6 только по новой команде. Для установки нужна внешняя подпись привычным способом.

# Предыдущий выпуск0.5.4: проверенный IPA опубликован

Нативная сборка, упаковка и тестовая публикация завершились успешно. Пакет независимо скачан и проверен; физическая приёмка на iPhone ожидается.

| Проверка | Результат |
| --- | --- |
| Версия / build | 0.5.4 / 88 |
| Исходный SHA / tag target | c44530eabe0d08a5b5182173a4c37d4fefabc568 |
| Workflow | [№88](https://github.com/Mr-EFES/NagramiX/actions/runs/38393655818), build и release success |
| Релиз | [v0.5.4](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.4), prerelease, не draft |
| IPA | [NagramiX-0.5.4-unsigned.ipa](https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.4/NagramiX-0.5.4-unsigned.ipa) |
| Размер | 85 414 344байта |
| SHA256 | 22770c8c8523cfac0815b7e0c4ac4dbad75e529474e77ce65b0feb9cb311f8ca |
| Платформа | ARM64, iOS15.0+, bundle com.mr-efes.nagramix, RU region, background audio |
| База | Telegram13.0, f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838, CURRENT |
| Входные параметры | clean_build=true, publish_release=true, prerelease=true, artifact_run_id пустой |

Независимая проверка `/workspace/.codex-validation-nagramix-054-build88-release`: SHA256SUMS и BUILD-PROVENANCE совпали с файлом, source SHA/pin/run; tag указывает на тот же commit; ZIP CRC цел. Все6Mach-O ARM64, minimum15.0/background audio подтверждены. Нет временных _CodeSignature/embedded profiles. Основной RU ресурс14863ключа; все274RU/200EN значений NagramiX побайтно по значению совпали с исходниками. Все31мелодии проверены; два новых onboarding PNG и26RU/EN Tour значений прошли штатный validator. Тело релиза совпадает с [русской аннотацией](releases/0.5.4.md).

Попытка[№87](https://github.com/Mr-EFES/NagramiX/actions/runs/38393039193) завершилась до компиляции из-за повторного включения PNG в AppResources/Lib.data и ios_application.resources. Удалён второй владелец, добавлена точная проверка native glob/единственного AppResources. Assets/manifest/loader прежние; чистый proof453файла,452прежних относительно87, только BUILD изменён. Исправление проверено успешным Bazel analysis/compile/package№88 и наличием PNG в IPA. Версия обеих попыток0.5.4.

Включены свайпы настроек, архивная одиночная пересылка/рассылка/Save, proxy sync и DNS Telegram, onboarding, skip call rating и [исправления стабильности](STABILITY_AUDIT.md). Нативная компиляция10новых/изменённых функций подтверждена; device_pending сохранён. XCTest и физические AVFoundation/Photos/сеть/доставка/жесты не проверялись. Компиляция не доказывает отсутствие всех ошибок; [приёмка iPhone](IPHONE_TEST_0.5.4.md).

Следующий рабочий выпуск0.5.5 только по новой команде; повторы текущей версии сохраняют0.5.4. Операции этой сборки не удаляли старые releases/tags/assets. Финальная сверка API: релизыv0.5.4/v0.4.5 доступны, releasev0.5.3 возвращает404при сохранённом теге8c0c117; в начале задачи релизыv0.5.3/v0.5.1 присутствовали. Кто/почему изменил их состояние, не установлено; восстановление вне текущей сборки не выполнялось. Последующие commits документации не являются source SHA этого IPA. Требуется внешняя подпись, например SideStore.
