# Аудит оформления NagramiX

Дата: 2026-10-05. База Telegram-iOS 12.9.2, pin `6ad963e5b62d354da79040f388ae2b9132fb17b8`. Платформа iOS/Swift; реальные механизмы — PresentationTheme, PresentationData, SwiftSignalKit, ItemListPresentationData и ComponentFlow. Android ThemeDescription/ResourcesProvider/ActionBar здесь не применяются.

## Дефект пользователя

Пользователь сообщает об исчезновении верхних actions/кнопки сообщения в светлой теме. В сообщении с заданием изображения нет. Повторный скриншот и путь к экрану запрошены. Точный View, его состояние enabled/disabled/alpha и причина этого конкретного дефекта пока не подтверждены. Не приписывать скриншоту исправления другого экрана и не считать этот regression пройденным.

Проверены кандидаты: stock PeerInfoHeaderNode, PeerInfoHeaderActionButtonNode, PeerInfoHeaderNavigationButton, NavigationButtonComponent, ChatTextInputPanelNode. NagramiX не подменяет их палитры. Header использует itemPrimaryTextColor/itemAccentColor на обычной surface и белые цвета на avatar/profile-color surface; это штатная Telegram логика. Native send control получает chat.inputPanel theme. Без скриншота/устройства нет оснований менять эти компоненты наугад.

## Аудит добавленного UI и изменения

| Элемент | Реальные штатные ключи / обновление | Результат исходников |
| --- | --- | --- |
| Категории Интерфейс/Функции/Прочее | rootController.navigationBar.primaryTextColor; theme didSet + ComponentFlow identity | Вместо composer panelControlColor используется цвет navigation surface; stock общий компонент неизменён |
| Поиск NagramiX | navigationSearchBar.inputFillColor/inputTextColor/inputPlaceholderTextColor/accentColor/inputIconColor/inputClearButtonColor | Loupe/Clear как SearchBarNode; clear не зависит от системного UIKit tint; rebind перерисовывает иконки |
| Cards, секции, switches, disclosure, descriptions | ItemListSwitchItem/DisclosureItem/SectionHeaderItem/TextItem | Штатные cells с ItemListPresentationData; theme входит в entry equality и controller signal |
| Proxy/DNS UI | Те же ItemList/ProxySettingsServerItem/ActionItem; AlertScreen updatedPresentationData | Серверы, ping, проверка/DNS/таймер не изменены |
| ID/дата/взаимный контакт | PeerInfoScreenLabeledValueItem .accent/.primary; list.itemAccentColor; profile/container native relayout | Настройка/свойство сервера/данные не изменены |
| Архив, корзина | chat.message.incoming/outgoing.secondaryTextColor | Видимый текст/иконка уже semantic; .black в недисплейном measurement заменён на тот же ключ |
| Контекстное меню | actionSheet.primaryTextColor/destructiveActionTextColor, semantic .primary/.disabled/.destructive | Иконки получают текущую theme из callback; native ContextController/Alert обновляют тему |
| История правок / локальное редактирование | richTextAlertController и AlertScreen updatedPresentationData | TextAlertContentNode.updateTheme штатно обновляет foreground; локальный editor получает поток presentationData |
| Подтверждение истории, action | list.itemCheckColors.fillColor/foregroundColor — как SolidRoundedButtonTheme(theme:) | Фиксированный #2f80ed/white заменён на пару theme keys; main-queue presentationData subscription/dispose |
| Media backdrop/надписи истории | Затемнённое full-screen media, фиксированные white/black как stock Stories | Это не обычная light surface. Лёгкий blur/preview/закрытие/seen gate сохранены, механической замены нет |
| Settings icon assets / app branding | renderSettingsIcon, штатные цветные подложки Telegram | Это stock style цветных иконок и branding, не отдельная theme palette; белая часть находится на цветной подложке |
| Bottom navigation, header, send control, стандартное оформление | Stock Telegram | Фабрики, Font.swift, стандартные tabs/theme settings не изменены; никакой собственной theme engine |

Новая начальная тема — встроенная «Тёмная» (.nightAccent), только когда запись presentationThemeSettings отсутствует. Seed через updateSharedData завершается до получения первого PresentationData. Любая сохранённая Light/Dark/Night/System/custom entry возвращается без изменений. System/timeBased/brightness механизмы Telegram и все fonts/сохранённые параметры масштабирования остаются штатными.

Не создавались NagramiX Light/Dark/Black, новые палитры, проверки isDark для выбора white/black, polling или глобальные overrides цвета. 24 stock файла защищены побайтно при overlay. Размеры custom поиска/категорий и backend работающих функций не изменены.

## Проверки

Применение overlay к чистому pin, сравнение с baseline, Python/Swift syntax и метаданные — пройдены. Нативная clean ARM64 сборка текущего SHA — ожидается; этот статус не относится к ранее опубликованному IPA №68. Новый workflow запрашивается без restore/save Bazel cache и без публикации/перезаписи релиза.

| Приёмка | Статус |
| --- | --- |
| Light: главный экран, профиль/action message/send, chats, settings, NagramiX, меню, поиск, recipient picker | Нужен запуск на iPhone; не проверено |
| Dark/Tinted: те же экраны | Не проверено |
| Night/Black: те же экраны | Не проверено |
| Light → Dark → Light → Night → Light без restart | Подписки и rebind проверены в коде; визуально не проверено |
| Custom theme | Semantic keys сохраняют поддержку; визуально не проверено |
| Обычный/увеличенный системный размер текста | Типографика не заменялась; устройство не проверено |
| Clean install Dark → ручной Light → restart Light; System/Auto Night | Missing-entry guard проверен в коде; физическая приёмка ожидается |
| Точный сценарий скриншота | Заблокирован отсутствующим изображением/путём к экрану |

До выполнения визуальных пунктов задача полностью не закрыта. Нативная компиляция не доказывает контраст или корректную отрисовку на iOS 27.

При смене keyboardAppearance в активном поиске используется штатный SearchBarNode pattern resign/becomeFirstResponder; guard исключает переактивацию при обычном вводе и прежнем стиле. Clear rightView скрывается режимом .never на пустом запросе, чтобы UIKit не возвращал пустую кнопку при layout. Первая чистая попытка №69 остановлена для включения этой необходимой live-theme правки; итоговую сборку следует проверять по новому SHA.

UIKit search/clear views инициализируются lazy из main-queue apply, а не во время async создания ListViewItemNode. Итоговый native build запускается после этой проверки потоков создания UI; промежуточная попытка №70 остановлена.
