# Аудит оформления NagramiX

Актуальная интеграция перенесена на Telegram 13.0; [аудит миграции](TELEGRAM_13_MIGRATION.md). Ранее указанные результаты №79 и локальных отдельных проверок относятся к прежней базе; новый нативный результат фиксируется отдельно.

Обновлено 2026-10-07. База — официальный Telegram-iOS 13.0, pin `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`. Используются реальные iOS API: PresentationTheme, PresentationData, SwiftSignalKit, ItemListPresentationData и ComponentFlow. Android ThemeDescription/ResourcesProvider к этому проекту не относятся.

## Пять референсов и найденный путь ошибки

1. Оформление → светлая тема с House, ночная автоматика выключена.
2. Настройки собственного профиля: видны «Сменить эмодзи-статус», «Изменить цвет профиля», «Изменить фотографию».
3. Оформление → облачная тема Chick.
4. Те же настройки профиля: строки и иконки исчезают, separators/background остаются. Пользователь также сообщает о пропавших кнопках отправки.
5. Желаемые начальные параметры: ночной режим «Системная», выбранная ночная тема «Тёмная».

Конкретные три строки созданы в `PeerInfoSettingsItems.swift` как `PeerInfoScreenActionItem`, IDs 0/1/2. `PeerInfoScreenActionItemNode.update` использует штатный `theme.list.itemAccentColor` и для NSAttributedString, и для generateTintedImage. Сам View и его alpha не патчились. Общий акцент поступает из customizeDefaultDayTheme; он также задаёт selectedIconColor/selectedTextColor, navigation buttonColor, actionSheet accents и chat.inputPanel.actionControlFillColor. Это общий путь для нескольких пропавших элементов, а не отдельный дефект одной надписи.

В закреплённом загрузчике облачных TelegramThemeSettings используется `UIColor(argb: settings.accentColor)`. UIKitUtils.swift вычисляет alpha как `(argb >> 24) & 0xff`. Значение legacy RGB24, например `0x00738c30`, даёт alpha=0. Светлый customizeDefaultDayTheme переносит этот прозрачный цвет в itemAccentColor и остальные action colors. Белая карточка и линии остаются, а текст/иконки становятся прозрачными. House использует встроенную тему без этого входного значения и потому читаем.

У штатной customizeDefaultDarkTintedPresentationTheme акцент далее пересоздаётся через HSB с alpha=1; поэтому тот же вход может выглядеть корректно в Dark, хотя Light переносит прозрачность напрямую. Эта разница подтверждена исходниками.

Это воспроизведённый дефект обработки входного формата, согласующийся с референсами. Сырые настройки конкретной серверной Chick пользователя не получены; точное значение этого цвета и результат на устройстве ещё не подтверждены. Не выдавать анализ/статические проверки за физическую приёмку.

## Исправление

Не заменяли текст на Color.BLACK, не меняли глобальные Telegram Theme keys и не создавали свою палитру. Исправлено только чтение accent/outgoingAccent в четырёх файлах:

| Генерируемый файл Telegram | Исправленных конверсий |
| --- | --- |
| TelegramPresentationData/Sources/MakePresentationTheme.swift | 4 accent + 4 outgoingAccent: все перегрузки загрузчика |
| SettingsUI/Sources/Themes/ThemeSettingsAccentColorItem.swift | 1: цвет выбранного облачного акцента |
| TelegramUI/Components/Settings/ThemeAccentColorScreen/Sources/ThemeAccentColorController.swift | 1: начальный акцент редактора |
| TelegramUI/Sources/OpenResolvedUrl.swift | 1: предпросмотр темы по ссылке |

Перед штатным UIColor(argb:) добавляется отсутствующий старший alpha byte только при `value >> 24 == 0`. RGB сохраняется; любой ненулевой ARGB alpha, включая полупрозрачный, сохраняется. Маска `0xff000000` — альфа-байт представления цвета, не чёрная палитра UI. Чёрный RGB24 0 также становится непрозрачным. Современный [API описывает ARGB](https://core.telegram.org/constructor/themeSettings); исправление поддерживает legacy RGB24, не отбрасывает alpha у современных ARGB, не меняет модель, сериализацию, серверные параметры или сохранённые preferences. Файловые темы и их native decoder не патчились.

Durable runtime-изменения находятся только в `ios/apply_features.py`. Добавлен Python helper применения точечных преобразований с точными count/anchor guards. Это интеграционный patch helper, а не runtime theme engine. Фабрики Day/Dark/Night/Tinted, их RGB-палитры, шрифты и layout не переписаны. Stock theme settings UI сохранён; в selector/editor изменено только чтение цвета. Защищены 28 appearance-файлов: 24 неизменны побайтно, для четырёх разрешён лишь точный ожидаемый результат конверсий и выбора варианта, описанного ниже. Общий UIColor(argb:) не меняется.

При выборе/переключении темы тот же native PresentationData pipeline строит PresentationTheme. Все существующие semantic bindings получают исправленный акцент; новых observers, polling, Light/Dark ветвлений или альтернативных UI нет. Перезапуск нужен для установки нового IPA, но последующие переключения остаются штатными live updates.

## Выбор варианта темы чатов — правка 0.5.1

Новые четыре референса: System/Night, System/Dark и сетка девяти тем при активном ночном режиме. Пользователь сообщает, что применение темы неожиданно делает оформление светлым. Сами скриншоты показывают тёмную сетку; сырые настройки конкретной применённой серверной темы и момент перехода на устройстве не получены.

Исследован stock ThemePickerController: сетка вызывает previewTheme(theme, nightMode), загрузка запрашивает .night/.classic, customApply передаёт selectThemeImpl(nil, initialThemeReference, true). Дальше selectThemeImpl загружает PresentationTheme без baseTheme. Миниатюры и stock makePresentationTheme(cloudTheme:dark:) уже выбирают весь набор .night/.tinted либо .classic/.day; два overload с baseTheme выбирают точное совпадение, иначе settings.first. Для settings=[day,tinted], baseTheme=night это first/day; миниатюра при этом dark/tinted. Потеря базы предпросмотра также не позволяет записать themePreferredBaseTheme для этого выбора.

В двух baseTheme overload MakePresentationTheme добавлен тот же stock подход выбора группы: exact → совместимая группа заданной базы → прежний first. При nil сохраняется прежний first, при отсутствии нужной группы сохраняется прежний fallback. Цвета, обои и palette берутся из выбранного TelegramThemeSettings, не синтезируются. ThemePickerController передаёт theme.referenceTheme.baseTheme в existing selectThemeImpl и использует baseTheme при загрузке варианта/обоев. Native запись themePreferredBaseTheme получает реально показанную базу.

Точная причина перехода для конкретного серверного набора пользователя без runtime-журнала не доказана; найденный путь несовпадения воспроизведён по исходникам и устранён. Никакой force/system/schedule state не изменён, новая theme engine/палитра не создана, factory defaults и шрифты сохранены. Уже сохранённый выбор не мигрируется/не сбрасывается: загрузчик исправляет несовпадающую базу при наличии совместимого варианта. Одновариантная custom theme сохраняет прежнее поведение: отсутствующий тёмный вариант не изобретается.

## Первый запуск

При отсутствующей записи presentationThemeSettings, до первого UI:

- `PresentationThemeSettings.defaultSettings` — штатная дневная `.dayClassic`;
- `AutomaticThemeSwitchSetting(force: false, trigger: .system, theme: .builtin(.nightAccent))` — «Системная» / «Тёмная»;
- `guard entry == nil else { return entry }` — сохранённый выбор не перезаписывается.

Светлая iOS использует дневную тему, тёмная iOS — выбранную ночную «Тёмную». Нельзя одновременно следовать System и всегда принудительно показывать Dark при светлой iOS. Это точные параметры пятого референса; определение системного стиля полностью остаётся у Telegram. Off, Schedule, Auto, Light, Night и custom после ручного выбора сохраняются. Русский cold-start/авторизация/внутренний интерфейс сохранены, настройки языка не изменены.

## Добавленный UI

Предыдущие semantic bindings сохранены: категории — navigationBar.primaryTextColor; поиск — navigationSearchBar inputFill/Text/Placeholder/Icon/Clear/Accent colors; карточки/switches/секции — native ItemList cells; proxy/DNS — native proxy/list/alert; ID/дата/взаимный контакт — PeerInfo labels/itemAccentColor; удалённая метка/корзина — incoming/outgoing.secondaryTextColor; меню — actionSheet keys; кнопка истории — itemCheckColors.fillColor/foregroundColor. Для поиска сохранён native pattern обновления активной клавиатуры и main-queue создания UIKit views. Media backdrop/white надписи истории относятся к постоянной затемнённой media surface, как у stock Stories.

В этой задаче не менялись категории, поиск, архив, Stories/read gate, задняя камера/жесты, прокси/DNS, широкие посты, ID/дата/взаимный контакт, пересылка, default-чекбоксы. Нет NagramiX Light/Dark/Black и собственной theme engine. Ни один новый пользовательский пункт оформления не добавлен.

## Проверки и состояние сборки

- Старый и новый apply_features применены к чистым validation копиям точного pin. Два ожидаемых generated-файла отличаются, остальные 224 файла проверочного дерева совпадают. Это scoped validation tree, не полный checkout Telegram.
- Защита штатных файлов и tree-sitter-разбор двух изменённых Swift-файлов проходят; синтаксис Python, согласованность метаданных и git diff --check также проверены. Удаление ожидаемого загрузчика/якоря применения и повторное наложение новой правки корректно отклоняются. Проверены 13 русских строк приветствия. Фабрики палитр, автоматическое переключение и defaults не изменены.
- Проверка официальной базы с --require-current: CURRENT, Telegram-iOS 13.0, SHA f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838; закреплённая и официальная версии совпадают.
- Чистая нативная сборка №75 на macOS/Xcode подтвердила компиляцию сохранённой правки тем в прежнем выпуске. Новый 0.5.1 ещё собирается; локально toolchain отсутствует. Physical acceptance ожидается.

Будущая приёмка: все девять тем из сетки и карусели; System/Dark и System/Night на тёмной iOS, System на светлой iOS; Off/manual Light/Night, Schedule/Auto; предпросмотр → применить/отменить, смена темы без restart, повторный cold start. Проверить фон/пузыри, действия профиля и отправку, а также исходные Light/RGB24 regression cases. План — [IPHONE_TEST_0.5.1.md](IPHONE_TEST_0.5.1.md). Физическую визуальную приёмку пока не считать выполненной.
