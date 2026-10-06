# Аудит оформления NagramiX

Обновлено 2026-10-06. База — официальный Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`. Используются реальные iOS API: PresentationTheme, PresentationData, SwiftSignalKit, ItemListPresentationData и ComponentFlow. Android ThemeDescription/ResourcesProvider к этому проекту не относятся.

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

Durable runtime-изменения находятся только в `ios/apply_features.py`. Добавлен Python helper применения точечных преобразований с точными count/anchor guards. Это интеграционный patch helper, а не runtime theme engine. Фабрики Day/Dark/Night/Tinted, их RGB-палитры, шрифты и layout не переписаны. Stock theme settings UI сохранён; в selector/editor изменено только чтение цвета. Защищены 27 appearance-файлов: 24 неизменны побайтно, для трёх разрешён лишь точный ожидаемый результат конверсий. Общий UIColor(argb:) не меняется.

При выборе/переключении темы тот же native PresentationData pipeline строит PresentationTheme. Все существующие semantic bindings получают исправленный акцент; новых observers, polling, Light/Dark ветвлений или альтернативных UI нет. Перезапуск нужен для установки нового IPA, но последующие переключения остаются штатными live updates.

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

- Overlay применён к двум чистым validation деревьям закреплённой базы: предыдущий HEAD и текущие изменения.
- Generated diff — ровно пять файлов: четыре конверсии плюс AppDelegate начальных настроек. Остальные 921 файла совпадают.
- Tree-sitter Swift syntax пяти файлов, Python syntax, metadata, 13 RU intro strings и diff check — пройдены. Это не native typecheck.
- Проверены значения RGB24 black/blue/green/white, opaque ARGB, alpha128 и alpha1: RGB сохраняется, нулевая alpha становится255, ненулевая остаётся исходной. Это проверка представления/конверсии, не отрисовки iOS.
- Native compile, warnings и запуск текущих изменений не проверены: пользователь явно запретил сборку без новой команды. Workflow не запускался.
- Предыдущая clean-сборка №71 была успешной, исходный SHA `65b118088bdf9776e8bf0a5cb21b51a3041e3dd1`, но НЕ содержит этих новых изменений. Релизный IPA №68 также прежний. Нельзя выдавать их за исправленную сборку.

| Приёмка новых исходников | Статус |
| --- | --- |
| House → Chick → профиль: три действия/иконки | Причина обработки выявлена и исправлена в коде; нужен новый IPA/физический тест |
| Кнопка отправки, выбранная вкладка, меню, поиск | Общий источник акцента исправлен; физически не проверено |
| Light / Dark-Tinted / Night-Black / custom | Палитры сохранены; визуально не проверено |
| House → Chick → House, Light → Dark → Light без restart | Native updates сохранены; визуально не проверено |
| Обычный/увеличенный текст | Fonts/layout не изменены; физически не проверено |
| Clean install System/Dark + manual choice/restart | Missing-entry seed проверен в коде; нужен физический тест |

Полный план — [IPHONE_TEST_0.4.3.md](IPHONE_TEST_0.4.3.md). Следующий шаг: только после отдельной команды собрать новый IPA, затем повторить эти сценарии на iPhone 17 Pro Max / iOS 27.0 / SideStore. Полную визуальную приёмку пока не считать завершённой.
