# Миграция тестового выпуска на Telegram 13.0

Пользователь выбрал актуальную официальную базу для NagramiX 0.4.9. Закреплён Telegram-iOS 13.0, commit `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`. Проверка актуальности CURRENT; moving branch и исключения из проверки не используются. Нативная компиляция пока ожидается.

## Совместимость

Официальная база требует Xcode 26.6, Bazel 9.2.0 и macOS 26. Xcode 26.6 присутствует в штатном macos-26 runner. Deployment target приложения в Telegram/BUILD — **iOS 15.0**; прежний минимум iOS 13 к новой базе не относится. Версия NagramiX остаётся 0.4.9.

## Адаптация

- DNS: системный путь сохраняет native coalescing, timeout и take:1 новой базы. Custom DoH и fallback прежние. Переподключение Network перенесено с удалённого поля mtProto на native mainSession; выполняется на его queue, учитывает shouldKeepConnection и не пробуждает приостановленный фон.
- Account: наблюдатель DNS и proxy failover размещены перед native mediaBox-операциями, с прежними cleanup и supplementary guard. Новые telemetry/engine guards не удаляются. Stock выбор движка не меняется: iOS использует MtProtoKit по умолчанию, Rust default относится к macOS.
- Камера: реальные CameraOutput и LegacyCamera теперь в CameraLegacy. Перенесены прежние initial rear/fallback/position/zoom hooks; публичный Camera façade, переключение и обработчики записи не заменяются.
- Настройки: собственные равные вкладки используют новые fillSlotWidths; штатные вкладки не меняются. NagramiX section вставляется перед myProfile с сохранением новой wallet section. Mutable Force TCP parameters и wide-post gutter адаптированы к текущим точным фрагментам.
- Архивный плеер: helper учитывает новую сигнатуру richMessageQueueId и сохраняет её штатный guard; архивная копия по-прежнему наблюдает recentActions playlist.
- Скачивание: увеличиваются только native workers разрешённых частей по 1 MiB. Общие native main/CDN лимиты и requests-per-worker сохраняются; OFF не меняет пул. Проверка насыщения перед dispatch и сам dispatch используют одинаковые лимиты. Прочие запросы ограничены своим штатным пулом даже после ускоренного скачивания.
- Русский: добавлены 20 новых ключей текущей базы с сохранением параметров форматирования и полными названиями действий.

Все остальные подготовленные модификации сохраняются: панель канала, двойной тап/реакции, меню архива и readonly avatar, отдельные пересылка/рассылка, фоновые видео, JPEG и сохранённые кружки. Persisted keys/defaults, стандартные темы и шрифты не переопределялись миграцией.

## Проверка исходников

Аудит использует полное Git tree без усечения. В первоначальной области 305 upstream-файлов изменились 155, отсутствующих путей нет. Затем добавлены референсы CameraLegacy и engine/build API; 326 исходных blobs сверены с SHA нового pin, Make/versions также сверены отдельно.

Полный строгий apply_features проходит; все мигрированные вставки используют replace_unique. Записаны 306 exact unique операции; 612 отдельных проверок primitive guard отклоняют отсутствующий/дублированный anchor. Это проверка механизма вставок, не интеграционный runtime-тест. Generated code после форматирования и усиления guards побайтно совпадает с проверенным результатом миграции.

295 Swift-файла разобраны tree-sitter без новых ошибок; восемь ограничений parser также воспроизводятся на stock raw. Полная apply_overlay, Make anchor, branding, все восемь иконок, 13 RU intro строк, Python syntax, metadata и diff checks проходят. Локальная проверка конфигурации использовала фиктивные значения только в /tmp; секреты репозитория используются исключительно нативным CI workflow.

Swift type checking, реальные жесты/декодер/MTProto и отсутствие крашей подтверждаются только новой macOS-сборкой и физическим тестом. Текущие изменённые функции compile_pending/device_pending. План приёмки — [iPhone](IPHONE_TEST_0.4.9.md); результат сборки — [статус](RELEASE_STATUS.md).

## Совместимость custom строк SettingsUI после нативной проверки

Сборка №81 обнаружила переход базового ListViewItem с previousItem/nextItem на ListViewItemNeighbors. NagramiXPercentageItem и NagramiXSettingsSearchItem переведены на новые точные сигнатуры; itemListNeighbors получает topFacet/bottomFacet из descriptors по штатному образцу ItemListTextItem. Neighbor descriptor предоставляет общий native ItemListItem extension. Это адаптация интерфейса, без изменения геометрии, значений, callbacks и поиска.

Дополнительно проверены по Git blob SHA четыре файла Display/ItemListUI (всего330 references). Fresh full overlay меняет только два custom settings files относительно №81; остальные generated files совпадают, четыре references сохраняются исходными. Обе Swift-функции в каждом классе совпадают с native protocol signatures, синтаксис проходит. Нативный результат приложения ещё ожидается; №81 failed, публикация skipped.
