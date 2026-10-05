# Текущий контекст NagramiX 0.4.3

Обновлено: 2026-10-05 (Москва). Единственная ветка — main, upstream origin/main.

## Текущая задача

После физической установки 0.4.3 пользователь сообщил: при включённом значке взаимного контакта он не виден в контактах и отсутствует в профиле. Исправлены исходники для следующей сборки, без запуска нового workflow и изменения опубликованного IPA.

## Исправление взаимного контакта после сборки №68

В ios/apply_features.py заменена прежняя вставка NSTextAttachment в конец имени: TextNode upstream ожидает UIImage под attachment key, поэтому прежний тип несовместим; длинные имена также обрезают хвост. Теперь ContactsPeerItem показывает «⇄ Взаимный контакт» перед прежним статусом, accent-цветом и штатным statusFont. Для picker без статуса — компактный ⇄ перед именем без изменения высоты. Последняя активность сохраняется, но хвост второй строки может штатно обрезаться на узком экране; VoiceOver получает полный статус.

В PeerInfoProfileItems добавлена отсутствовавшая строка взаимного контакта, обычная PeerInfoScreenLabeledValueItem, уникальный ID11002. В обоих местах требуются реальный .mutualContact, не self/bot и непустое имя. Серверный флаг не зависит от разрешения на телефонную адресную книгу; не помечать все контакты взаимными. Сохранённый checkbox/default и прочие метаданные не изменены.

В ContactsPeerItemNode/PeerInfoScreen добавлены main-queue observers только изменения showMutualContactIcon, weak self/cleanup. Переключатель обновляет открытые представления. Добавлена локализованная строка в NagramiXCore RU/EN и PresentationStrings. Спецификация mutual-contact-badge.md актуализирована.

Проверено применение baseline/current overlay к pin, сохранение 18 защищённых stock-файлов, синтаксис Python/Swift, RU локализация и метаданные. Сравнение generated дерева ограничено ContactsPeerItem, PeerInfoProfileItems, PeerInfoScreen и добавленными строками NagramiXCore. Нативная компиляция изменённых исходников и физическая проверка НЕ выполнены; registry profile_info compile_pending. Опубликованный IPA сборки №68 остаётся прежним.

## Изменения выпуска

- ios/apply_features.py: отсутствующий сохранённый язык больше не приравнивается к установленному ru в AuthorizationSequenceSplashController. Теперь первый переход скачивает и сохраняет русский пакет до авторизации; приветствие учитывает сохранённый ручной язык при добавлении аккаунта.
- ManagedLocalizationUpdatesOperations: getLocalization и оба отсутствующих LocalizationSettings используют ru/Русский вместо en/English. Это устраняет путь, который после входа запрашивал и сохранял английский поверх русского интерфейсного fallback. Существующая сохранённая локализация остаётся источником ручного выбора.
- PresentationData: под пустым/неполным русским пакетом сохраняется полный bundled RU словарь; русские строки не падают на английский. Словарь кэшируется. Splash также передаёт languageCode в dictFromLocalization. Common.Edit переопределён на «Изменить» в downloaded/cached RU и в ios/Resources/ru.lproj/Localizable.strings.
- Удалено собственное изменение systemUserInterfaceStyle в AppDelegate: начальный выбор и отслеживание темы теперь stock. Default settings, defaultPresentationData и factories/palettes — upstream.
- Доработанные категории NagramiX генерируются отдельными NagramiXItemListControllerSegmentedTitleView и NagramiXHorizontalTabsComponent в прежних Bazel targets (srcs glob). Stock-файлы этих компонентов больше не патчатся. ItemListController содержит отдельный equalSectionControl case/state; исходная sectionControl ветка не изменена. Устранено попадание custom clipsToBounds/layout/font изменений в общие stock-компоненты; причинность конкретного визуального дефекта без устройства не подтверждена.
- Добавлена fail-fast защита 18 stock-файлов: themes/settings/chat themes/font/shared tabs. После overlay байты должны совпадать с чистой закреплённой базой. Исключение — собственные иконки приложения в отдельном ThemeSettingsAppIconItem, сохранённый брендинг пользователя.

## Лёгкий blur предпросмотра истории

В ios/apply_features.py заменён источник картинки NagramiXStoryConfirmationController: photoDatas с autoFetchFullSize=true, только завершённые реальные image data; video — largest previewRepresentation через штатные fetchedMediaResource/resourceData. Встроенная маленькая immediateThumbnail больше не увеличивается до экрана. UIImage сохраняет правильное соотношение сторон через scaleAspectFill; убрана принудительная отрисовка любого источника как 1080×1920. Слой blur .dark/alpha0.5 и затемнение0.18 оставлены как в первом принятом варианте, без добавления второго размытия. Фото/видео и начальная/следующая история используют общие helper-пути.

Скачивается только фото или обложка видео; видео целиком не запрашивается. Пока изображение не загрузилось (либо отсутствует previewRepresentation/сеть), фон нейтральный чёрный, подтверждение и отмена доступны. Нельзя обещать отображение деталей недоступного медиа. Подписки и fetch отменяются при закрытии через прежний previewDisposable.

Сравнение overlay до/после: изменён только StoryContainerScreen.swift. Swift-синтаксис проверен; тела closePressed/confirmPressed/nagramiXCanMarkStoryAsSeen совпадают, весь StoryContainerScreen после нормализации четырёх preview expressions и их типа совпадает побайтно. Логика подтверждения, отмены, навигации, per-story approval и seen-state сохранена. Нативная сборка №68 прошла; визуальная проверка на iPhone ещё отсутствует.

## Заголовок звонков в «Прочее»

В ios/Sources/SettingsUI/NagramiXSettingsController.swift добавлен otherCallsHeader во вкладку other перед Force TCP. Использует тот же ItemListSectionHeaderItem/локализованный nagramiXCallsHeader/section calls, что заголовки соседних вкладок. Отдельный stableId49, исключён из результатов поиска; поиск Force TCP по группе «Прочее · Звонки» сохранён. callsHeader и подтверждение исходящих звонков во вкладке «Функции» сохранены. Переключатель, сохранение forceTcpCalls и VoIP integration не изменены. Проверены применение overlay, синтаксис Swift и метаданные; нативная компиляция прошла в сборке №68, визуальная проверка ожидается.

## Значения переключателей при первом запуске

В NagramiXTabSettings.current изменены только девять отсутствующих-key fallback false→true: wideChannelPosts/useRearCameraForVideoMessages/hideStories/disableStoryCameraSwipe/confirmStoryViewing/enableStoryRepost/showProfileIds/showRegistrationDate/showMutualContactIcon. Остальные перечисленные пользователем значения уже соответствуют запросу: hideContacts/hideCalls/showProxyButton/hideProxySponsorChannel/showForwardWithoutAuthor/showSelectByAuthor/confirmOutgoingCalls=true, showDeletedMessages/messageEditHistory/forceTcpCalls=false. Неназванные showSearchButton/proxyAutoSwitchEnabled остаются false; DNS system/таймер15 без изменений.

object(forKey:) as? Bool ?? default сохраняет явный false, а не заменяет его новым default. Ключи, write/update и legacy migration спонсора не менялись; повторные старты/обновления не сбрасывают ручной выбор. Проверены все 19 запрошенных default-позиций, синтаксис, применение overlay и метаданные; нативная компиляция прошла в сборке №68, первый запуск на устройстве ожидает проверки. product/SETTINGS.md и спецификация широких постов актуализированы.

## Проверки и границы

Overlay применён к Telegram-iOS 12.9.2, SHA 6ad963e5b62d354da79040f388ae2b9132fb17b8. Проверено сохранение 18 stock-файлов, stock sectionControl/defaultPresentationData и начальной темы AppDelegate; сравнение с baseline выявляет только целевые изменения и новые изолированные компоненты. Остальные функции совпадают побайтно. Python syntax, Swift tree-sitter syntax, intro localization, shell syntax, metadata и git diff проверены. Нативная компиляция, включая Swift typecheck, прошла в сборке №68. Получен физический отчёт об ошибке взаимного контакта; остальные проверки визуала на iOS 27 ещё не подтверждены.

Сохранённый английский из старого сбойного запуска не отличим от ручного выбора английского. Его автоматически не сбрасываем; новый чистый вход исправлен. Старые сохранённые Tinted/другие предпочтения также не сбрасываем. Проверить чистое состояние отдельно от обновления без потери локального архива.

## Сборка и публикация

[Тестовый релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.3) опубликован 2026-10-05; [сборка №68](https://github.com/Mr-EFES/NagramiX/actions/runs/37328777156) прошла успешно. Исходный SHA `371eb84e9b0c2845856dd9d6809015e8166a84bb`. SHA-256 `de31cdbc398234aac40c9241d27e2a8cb8c0cf1fa9bb8f091d2745b1d490688f`. Размер 73 888 480 байт. Скачанный IPA проверен: версия 0.4.3/build 68, ARM64, bundle com.mr-efes.nagramix, русский development region, 14843 RU строк с полным Common.Edit «Изменить» и 179 custom RU строк, отсутствие signatures/profiles, правильные provenance/checksum. Это отдельный новый IPA; прежние файлы не заменены. [Статус](PENDING_RELEASE.md), [план](IPHONE_TEST_0.4.3.md).

## Сохранённые функции

Прокси, DNS, первый кружок/жесты, Stories/read gate, wide posts/мозаики, IDs/дата, вкладки/спонсор, поиск и архив не переписывались. Согласованные края/размеры поиска сохранены в custom-категориях. Ограничения архива: серверное закрепление/редактирование удалённого оригинала не восстанавливаются; медиа требуют кэша. Секундные proxy timers в фоне iOS не гарантированы.

## Следующий шаг

По отдельной задаче пользователя собрать обновлённые исходники, затем проверить взаимный/невзаимный контакт, включение/выключение без перезапуска, длинные имена, профиль, VoiceOver и обе темы. Текущий опубликованный IPA исправление взаимного контакта не содержит.

Установить опубликованный IPA через SideStore и пройти план на iPhone. Чистый первый запуск языка/default-переключателей проверять отдельно от обновления, которое сохраняет выбор и локальные данные. Записать результаты, затем исправлять по новым задачам пользователя. Нативная сборка и проверка IPA не доказывают отсутствие UI/runtime ошибок. GitHub main синхронизирован через exact SHA objects/update_ref force=false; поздний documentation commit не является исходным SHA IPA. Коммиты/отчёты — русские.
