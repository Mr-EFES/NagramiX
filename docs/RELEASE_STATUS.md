# NagramiX 0.5.8: подготовка тестовой сборки и релиза

Пользователь16октября разрешил новый IPA со всеми текущими правками и публикацию GitHub Release с описанием возможностей и отличий от стандартного Telegram. Версия0.5.8, native compile и пакет пока pending; физическая приёмка отдельно. Предыдущие releases/tags/assets не заменяются.

[Изменения](../product/releases/0.5.8.md) · [План iPhone](IPHONE_TEST_0.5.8.md).

# История проверки0.5.7/build93

Добавлено [автораскрытие спойлеров](../product/features/auto-reveal-spoilers.md): Функции/Сообщения, по умолчанию ON, сохранённый выбор имеет приоритет при холодном запуске. Текст и обычные фото/видео раскрываются без нажатия. Новая функция послеbuild93: source_checked/compile_pending/device_pending; сборка и физический тест ещё не выполнены.

После физического теста подготовлена [правка отрисовки архивного кружка](ARCHIVED_ROUND_VIDEO_FIX.md): убрать видимую цветную подложку под прозрачным видео и вернуть штатную анимацию масок. Source_checked/native_compile_pending/device_pending; **в переданный build93 не входит**, новая IPA не запрошена. Остальная работа локальных кружков по сообщению пользователя устраивает, визуальная приёмка пока не завершена.

Следующая подготовленная правка — [нижняя панель выделения](MESSAGE_SELECTION_ACTIONS_FIX.md): сохранить состав во время actions=nil, отключить действия до текущего ответа и убрать перемещение внутренних иконок. Source_checked/native_compile_pending/device_pending; также не входит вbuild93. Callback-пути и предыдущая правка кружка сохранены, новая сборка не запрошена.

Подготовлена [персональная страница уведомлений](NOTIFICATION_SOUNDS_FIX.md):23+8builtins внеcachegate, ownedrefresh/download и резервное defaultpreview по актуальномуdefaultCloud. Source_checked/native_compile_pending/device_pending; вbuild93 не входит. Реальная доставка/звук на iPhone не проверены, дополнительные симптомы запрошены у пользователя. Новая IPA не запрошена.

Подготовлена [правка mini-app кнопки в компактном списке](../product/features/compact-chat-list.md): вертикальное центрирование/резерв даты и адаптивная высота для крупного текста; штатный запуск сохранён. Source_checked/native_compile_pending/device_pending, вbuild93 не входит. Реальный tap/рисунок на iPhone ещё не проверены, новая IPA не запрошена.

Пользователь 16 октября отдельно разрешил push коммита 5a59266 в main и сборку для физического iPhone. Нативная компиляция, упаковка и загрузка завершились успешно 2026-10-16 в 14:27 UTC. Все правки после build92 и согласованные экраны включены. Пакет скачан и независимо проверен; физический тест ожидается. Публикация GitHub Release отключена, прежние релизы/теги/IPA сохранены.

| Параметр | Значение |
| --- | --- |
| Run | [38909507273 / build93](https://github.com/Mr-EFES/NagramiX/actions/runs/38909507273) |
| Source | `5a59266c9efd76e4b26c040159620894cf890a40` |
| База | Telegram13.0, `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`, CURRENT при сборке |
| Артефакт GitHub | `12051909165`, NagramiX-0.5.7-unsigned-arm64 |
| IPA | `/workspace/outputs/NagramiX-0.5.7-build93-unsigned.ipa` |
| Размер | 88 510 648 байт |
| SHA256 IPA | `92f6de745bd3e2af6667907cd5ce6a81c375a55229e1bd38c5fd1f943a4125a8` |
| Native / пакет / iPhone | compile_passed / проверен / device_pending |

Проверка `/workspace/.codex-validation-nagramix-057/artifact93`: SHA256 архива совпал с GitHub digest `95ccfca4143c854e545fab76fcd9bec58e50067b91c50b876fca60666e1c1555`. ZIP CRC архива и IPA, SHA256SUMS, BUILD-PROVENANCE, source/pin/run/version/build совпали. Все 6 Mach-O ARM64, minimum iOS15.0, background audio, основной icon1 и альтернативы2–8 для iPhone/iPad подтверждены. Временных подписей/профилей нет. Проверены 31 мелодия, RU14863 и все custom значения RU268/EN194, 26 Tour значений и размеры всех семи PNG; старого runtime atlas нет. Копия IPA в outputs имеет тот же SHA256. Штатный validator и независимая проверка пройдены.

Новые статусы story_controls, forward_copy, video_pip_swipe, double_tap_edit, branded_onboarding и advertising_visibility локально обновлены до compile_passed; device_pending сохранён. XCTest и реальный iPhone не проверялись. Итоговая документация изменена локально после сборки и не меняет source SHA пакета. clean_build=false, publish_release=false, prerelease=true; следующий рабочий выпуск0.5.8 только по отдельной команде. Для установки нужна внешняя подпись.

[Изменения](../product/releases/0.5.8.md) · [Приёмка](IPHONE_TEST_0.5.8.md).

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
