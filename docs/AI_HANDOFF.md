# Текущий контекст NagramiX 0.4.3

Обновлено: 2026-10-05 (Москва). Единственная ветка — main, upstream origin/main.

## Текущая задача

Пользователь разрешил собрать рабочую тестовую 0.4.3 для физической проверки на iPhone 17 Pro Max, iOS 27.0, SideStore. Включить все накопленные изменения: русский язык до/после первой авторизации, stock-оформление Telegram, лёгкий blur истории, заголовок звонков в «Прочее», согласованные переключатели первого запуска. Опубликовать как prerelease, не заявлять стабильность без устройства.

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

Сравнение overlay до/после: изменён только StoryContainerScreen.swift. Swift-синтаксис проверен; тела closePressed/confirmPressed/nagramiXCanMarkStoryAsSeen совпадают, весь StoryContainerScreen после нормализации четырёх preview expressions и их типа совпадает побайтно. Логика подтверждения, отмены, навигации, per-story approval и seen-state сохранена. Это не новая нативная сборка и не визуальная проверка на iPhone.

## Заголовок звонков в «Прочее»

В ios/Sources/SettingsUI/NagramiXSettingsController.swift добавлен otherCallsHeader во вкладку other перед Force TCP. Использует тот же ItemListSectionHeaderItem/локализованный nagramiXCallsHeader/section calls, что заголовки соседних вкладок. Отдельный stableId49, исключён из результатов поиска; поиск Force TCP по группе «Прочее · Звонки» сохранён. callsHeader и подтверждение исходящих звонков во вкладке «Функции» сохранены. Переключатель, сохранение forceTcpCalls и VoIP integration не изменены. Проверены применение overlay, синтаксис Swift и метаданные; визуальная проверка и нативная компиляция ожидают следующей сборки.

## Значения переключателей при первом запуске

В NagramiXTabSettings.current изменены только девять отсутствующих-key fallback false→true: wideChannelPosts/useRearCameraForVideoMessages/hideStories/disableStoryCameraSwipe/confirmStoryViewing/enableStoryRepost/showProfileIds/showRegistrationDate/showMutualContactIcon. Остальные перечисленные пользователем значения уже соответствуют запросу: hideContacts/hideCalls/showProxyButton/hideProxySponsorChannel/showForwardWithoutAuthor/showSelectByAuthor/confirmOutgoingCalls=true, showDeletedMessages/messageEditHistory/forceTcpCalls=false. Неназванные showSearchButton/proxyAutoSwitchEnabled остаются false; DNS system/таймер15 без изменений.

object(forKey:) as? Bool ?? default сохраняет явный false, а не заменяет его новым default. Ключи, write/update и legacy migration спонсора не менялись; повторные старты/обновления не сбрасывают ручной выбор. Проверены все 19 запрошенных default-позиций, синтаксис, применение overlay и метаданные; нативная компиляция/первый запуск на устройстве ожидают следующей сборки. product/SETTINGS.md и спецификация широких постов актуализированы.

## Проверки и границы

Overlay применён к Telegram-iOS 12.9.2, SHA 6ad963e5b62d354da79040f388ae2b9132fb17b8. Проверено сохранение 18 stock-файлов, stock sectionControl/defaultPresentationData и начальной темы AppDelegate; сравнение с baseline выявляет только целевые изменения и новые изолированные компоненты. Остальные функции совпадают побайтно. Python syntax, Swift tree-sitter syntax, intro localization, shell syntax, metadata и git diff проверены. Это не Swift typecheck, не новая нативная сборка и не физическая проверка. Гарантировать устранение визуальных проблем на iOS 27 без следующего IPA нельзя.

Сохранённый английский из старого сбойного запуска не отличим от ручного выбора английского. Его автоматически не сбрасываем; новый чистый вход исправлен. Старые сохранённые Tinted/другие предпочтения также не сбрасываем. Проверить чистое состояние отдельно от обновления без потери локального архива.

## Сборка и публикация

Метаданные переведены на 0.4.3, подготовлена русская аннотация. Предыдущие IPA не переименовываются и не заменяются. После успешной сборки записать исходный SHA/run/build/checksum и проверить скачанный новый IPA. [Статус](PENDING_RELEASE.md), [план](IPHONE_TEST_0.4.3.md).

## Сохранённые функции

Прокси, DNS, первый кружок/жесты, Stories/read gate, wide posts/мозаики, IDs/дата, вкладки/спонсор, поиск и архив не переписывались. Согласованные края/размеры поиска сохранены в custom-категориях. Ограничения архива: серверное закрепление/редактирование удалённого оригинала не восстанавливаются; медиа требуют кэша. Секундные proxy timers в фоне iOS не гарантированы.

## Следующий шаг

Проверить актуальность upstream, запустить единственный workflow с publish_release=true/prerelease=true от main, дождаться успешной сборки, скачать и проверить IPA/ARM64/RU/resources/provenance/checksum/signature removal. Записать фактический результат в текущие документы/реестр/русскую аннотацию. GitHub git push ранее возвращал 401; публикация exact SHA через /tmp/nagramix-publish.py и update_ref force=false. Коммиты/отчёты — русские.
