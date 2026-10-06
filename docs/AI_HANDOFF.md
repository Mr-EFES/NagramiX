# Текущий контекст NagramiX 0.4.3

Обновлено 2026-10-06 (Москва). Единственная ветка main, upstream origin/main. Основа Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`. Проект overlay, не полный исходный fork. Все новые отчёты/коммиты/аннотации — русские.

## Текущая задача и запрет сборки

Пользователь прислал пять скриншотов. Light/House корректна; выбор Chick делает прозрачными три native action строки собственного профиля («Сменить эмодзи-статус», цвет профиля, фото), выбранную вкладку/другие акценты; также сообщается о невидимой отправке. Требуется stock Telegram оформление. Новый clean-install default: ночной режим «Системная», выбранная ночная «Тёмная». **Без отдельной новой команды пользователя сборку не запускать.** Нативная компиляция текущей правки и физическая проверка ожидаются; не заявлять стабильность.

## Что изменено после пяти скриншотов

Только runtime `ios/apply_features.py`:

1. apply_telegram_theme_color_compatibility: 11 строго проверенных чтений accent/outgoingAccent в MakePresentationTheme (8), ThemeSettingsAccentColorItem (1), ThemeAccentColorController (1), OpenResolvedUrl (1). При отсутствии alpha byte legacy RGB24 получает opaque alpha; RGB и ненулевой ARGB alpha сохраняются. Не меняется UIColor глобально, модель/сериализация TelegramThemeSettings, файловые темы или палитры. Современный API описывает ARGB; нужно поддерживать и старые RGB24. Конкретный raw payload Chick пользователя не получен, физическая причинность ещё требует проверки.
2. Начальный seed: guard отсутствующего entry; defaultSettings + automatic force=false/trigger=.system/theme=.nightAccent. Удалён прежний `.withUpdatedTheme(.nightAccent)` и принудительное Off. Дневная тема stock dayClassic; светлая iOS → dayClassic, тёмная → nightAccent. Существующие System/Off/Schedule/Auto/Light/Night/custom entries не перезаписываются, русский язык не меняется.
3. Защита 27 stock appearance-файлов: 24 полностью неизменны, три с точным whitelist ожидаемых конверсий; palettes/fonts/native actions/native theme settings layout защищены. OpenResolvedUrl сохраняет прежнюю story-link интеграцию.

Реальный View дефекта — PeerInfoScreenActionItemNode: NSAttributedString и icon tint берут list.itemAccentColor. Этот native код не меняется. customizeDefaultDayTheme переносит входной акцент также в selected tab/navigation/actionSheet/send fill. Цвет RGB24 при исходном UIColor(argb:) имеет alpha0, что объясняет пустые строки при сохранённых карточке/линиях. Исправляется общий источник чтения акцента, не отдельный black text hack. Подробные источники/ограничения — [THEME_AUDIT.md](THEME_AUDIT.md).

## Проверено

Baseline HEAD overlay и текущий overlay применены к чистым validation копиям pin. Ровно пять generated файлов отличаются (четыре конверсии и AppDelegate), остальные 921 совпадают. Новые source-файлы официальной базы дозагружены только для анализа. Tree-sitter Swift syntax пяти файлов, Python syntax, metadata, RU intro13, diff check пройдены. Проверены RGB24 black/blue/green/white и ARGB alpha255/128/1: RGB не меняется; восстанавливается только отсутствующая alpha.

Это статические проверки. Native compile/typecheck/warnings и визуал новой правки НЕ проверены; workflow не запускался по прямому запрету пользователя. Registry clean_install_defaults и standard_telegram_themes: compile_pending/device_pending. Остальные функции не менялись. Документация/спецификация/реестр/план физической проверки актуализированы; версия остаётся 0.4.3 до отдельной задачи выпуска.

## Предыдущие артефакты — не новые исправления

- Релиз [v0.4.3](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.3), IPA build68: исходный SHA `371eb84e9b0c2845856dd9d6809015e8166a84bb`; 73 888 480 байт; SHA256 `de31cdbc398234aac40c9241d27e2a8cb8c0cf1fa9bb8f091d2745b1d490688f`.
- Отдельная [clean-сборка №71](https://github.com/Mr-EFES/NagramiX/actions/runs/37355849502), [артефакт](https://github.com/Mr-EFES/NagramiX/actions/runs/37355849502/artifacts/11367297769): исходный SHA `65b118088bdf9776e8bf0a5cb21b51a3041e3dd1`; 73 888 976 байт; SHA256 `448818d0cf640d69e8888b1fdb658bbc97b497066fec56bdbfc711158ea8e2ea`. Полная compile/typecheck успешна, связанных Swift warnings не найдено. IPA проверен: ARM64, version0.4.3/build71, bundle com.mr-efes.nagramix, regionru, RU14843/custom180, «Изменить»/«Взаимный контакт», без signatures/profiles, provenance/checksum совпадают.
- №71 не содержит нынешней RGB24/ARGB/System-Dark правки. №68 не содержит также исправления взаимного контакта. Старые релиз/tag/assets не перезаписывались. Попытки69/70 ранее отменены для дополнительных исправлений поиска, не compile failures.

## Сохранённые функции и контекст

Русский: полный bundled RU fallback, скачивание/сохранение ru до первого входа, отсутствие английского fallback после авторизации/фонового updates, полное «Изменить». Ручной язык сохраняется; старый сбойный saved en не отличим от намеренного en и не сбрасывается.

Взаимный контакт: real TelegramUser.flags.mutualContact (не self/bot/nameless); «⇄ Взаимный контакт» перед прежним status, picker без status — компактный ⇄ перед именем. Native TextNode не принимает прежний NSTextAttachment. Профиль — PeerInfoScreenLabeledValueItem ID11002. Main-queue weak observers only toggle changes, cleanup. Контакты не зависят от разрешения phone addressbook для чтения server flag. Исправление вошло в №71, физическая приёмка не получена.

Категории NagramiX изолированы как equalSectionControl; native shared HorizontalTabs/sectionControl остаются stock. Custom categories используют navigationBar.primaryTextColor. Поиск — stock Loupe/Clear + navigationSearchBar semantic colors; lazy UIKit creation main queue, native keyboard resign/become при изменении style; геометрия full-width48/r24/y12/item71 сохранена. Header «ЗВОНКИ» в Прочее stableId49 перед ForceTCP, исключён из search.

Stories: качественный completed photoDatas / largest video preview, без tiny-thumbnail upscale; aspectFill/blur.dark alpha0.5/dim0.18. Подтверждение, отмена, approval/seen gate не менялись. Action — itemCheckColors fill/foreground, presentationData main queue subscription/dispose; белый media foreground на затемнённой surface сохранён.

Холодная запись заднего кружка: после permissions нужно новое удержание, не auto-start; pending cancel/dismiss сохраняются. Прокси: single phase15/30/60, fresh native ping перед failover, online не заменён ping, ограниченные probes/background pause, ручные actions не перебиваются stale transactions. Архив: local copy/edit/reply quote/select/delete, не восстановление server edit/pin; медиа требуют кэша. Timer в приостановленном iOS фоне не гарантирован. Эти пути, wide posts/mosaics, ID/дата, tabs/sponsor, forward/select/search и default19-checkbox positions в текущей задаче не менялись.

## Следующий шаг

Дождаться отдельной команды сборки. Затем собрать новый исходный SHA, проверить IPA/provenance/русские ресурсы и физически повторить House → Chick → профиль/send, выбранную вкладку, preview/editor/link, Light/Dark/Night/custom/live-switch/font-scale. Отдельно clean install System/Dark и сохранение ручного выбора/русского. [План](IPHONE_TEST_0.4.3.md), [статус](PENDING_RELEASE.md). Устройство iPhone 17 Pro Max, iOS 27.0, SideStore. Не выдавать старый IPA за текущий и не запускать workflow по собственной инициативе.
