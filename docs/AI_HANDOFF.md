# Передача контекста NagramiX

## Текущая база

- Дата: 2026-10-01 (UTC).
- Актуальная версия продукта: **0.3.9**.
- Статус: **опубликованный релиз 0.3.9 для device-регресса; stable подтверждается после физического теста**.
- Платформа: только iPhone/iOS.

## Состояние репозитория и GitHub

Исторической базой 0.3.9 остаётся линия 0.3.8 из `https://github.com/Mr-EFES/NagramiX`. В активном дереве release-файл, workflow сборки и workflow публикации переведены на 0.3.9.

В GitHub Actions сохранены только три необходимые workflow: аудит upstream pin, сборка неподписанного IPA и публикация релиза. Ветка `work` отправлена в GitHub, открыт PR #15. Первый build run `36140188656` подтвердил наличие `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` и дошёл до нативной Swift-компиляции, но обнаружил несовместимый тип placeholder в новом SearchBar. `NagramiXSettingsSearchHeader` исправлен: `SearchBarNode.placeholderString` теперь получает штатный theme-aware `NSAttributedString`, а не `String`. Повторный run `36142093146` успешно собрал, упаковал и загрузил артефакт `NagramiX-0.3.8-unsigned-arm64` размером 73 456 389 байт.

Для текущего checkout восстановлен remote `origin` на `https://github.com/Mr-EFES/NagramiX.git`. GitHub CLI авторизован с scopes `repo` и `workflow`; PR #16 влит в `main` merge-коммитом `a70dbd5c`. Publish run `36613861232` успешно создал публичный релиз `v0.3.9` и загрузил `NagramiX-0.3.9-unsigned.ipa` вместе с `BUILD-PROVENANCE.txt`. В `docs/BOOTSTRAP.md` описан безопасный неинтерактивный вариант авторизации. Секреты и токены в репозиторий не записывались.

В 0.3.8 исправление `ChatMessageBubbleItemNode` сохраняло широкую `maximumContentWidth` и расширяло финальные frame линейных content nodes, благодаря чему одиночное media и caption стали широкими. Mosaic-ветка grouped media обходит эту линейную финализацию: её positions заранее рассчитывались через `chatMessageBubbleMosaicLayout` со штатным `layoutConstants.image.maxDimensions.fittedToWidthOrSmaller(...)`, то есть со старым narrow cap. Поэтому внешний container мог быть широким, а альбом оставался узким. В 0.3.9 для wide broadcast post в штатный mosaic algorithm передаётся динамический `availableMosaicWidth`, вычисленный из той же `maximumContentWidth` за вычетом штатных image insets. OFF-ветка дословно сохраняет исходный Telegram `fittedToWidthOrSmaller`; собственная grid logic не добавлена. Для ON/OFF observer теперь запрашивает обновление каждого message id видимой группы, чтобы grouped positions создавались заново с текущим режимом.

В основной экран настроек добавлен постоянный theme-aware SearchBar сразу под сегментами «Интерфейс / Функции / Прочее». Непустой запрос фильтрует `nagramiXAllSettingsEntries`, то есть единую модель всех трёх категорий, и не использует активную вкладку. Индекс строится из локализованных title, description, section и category; результаты используют исходные entry cases и handlers, группируются как `Категория · Секция`. DNS и proxy-действия представлены поисковыми ссылками на существующий Proxy screen без новых preference keys. Очистка запроса возвращает текущую выбранную вкладку.

Исправлено неверное размещение SearchBar: прежний `ItemListControllerHeaderItem` фреймворк закреплял в абсолютной точке `(0, 0)` controller node, из-за чего поле попадало под navigation/segmented area и могло некорректно принимать касания. Теперь search bar является первым штатным `ListViewItem` списка. Он располагается после navigation bar с сегментами и перед первым заголовком настроек, использует list safe insets, остаётся видимым при пустой выдаче и продолжает управлять тем же глобальным query pipeline.

Visual state удалённых сообщений теперь использует реальный `NagramiXArchivedMessageAttribute`. Для archived bubble основной Telegram content, background, actions и reactions явно получают alpha 0.5, а при каждом normal bind alpha возвращается к 1.0. Отдельная недиммированная footer-строка резервирует 22 pt и справа показывает существующую theme-tinted delete icon и локализованную/пользовательскую метку, поэтому status не пересекается с date/views/edited. Новый ключ `nagramix.messages.deletedMessageLabel` хранит нормализованную однострочную строку до 64 символов; пустое значение использует `Удалено`/`Deleted`. Editor построен на штатном `AlertScreen` + `AlertInputFieldComponent`, а notification перепривязывает видимые сообщения без restart. Backend архива и существующий showDeletedMessages key не менялись.

Документация репозитория ведётся на русском языке. Английский допускается только в коде, стабильных идентификаторах, названиях внешних API и локализационных таблицах, где он необходим по назначению.

## Проверка и следующий шаг

Для 0.3.9 прошли Python compile, JSON/YAML/shell/whitespace проверки и полное применение overlay к чистому Telegram-iOS `6ad963e5b62d354da79040f388ae2b9132fb17b8`. В применённом Swift проверено, что wide mosaic получает adaptive width, OFF сохраняет stock expression, а refresh перечисляет все message ids группы. Перенос поиска в первый list item и deleted visual/settings pipeline проверены Swift parser и структурными assertions. Нативная macOS ARM64-сборка обновлённой 0.3.9 успешно выполнена в GitHub Actions; runtime-проверка deleted cell reuse/media/footer на физическом iPhone ещё не выполнена.

Исправление wide posts статически проверено повторным успешным применением полного `ios/apply_overlay.py` к чистому pinned checkout Telegram-iOS `6ad963e5b62d354da79040f388ae2b9132fb17b8`, а также структурными проверками общей width pipeline. Linux-среда не может выполнить визуальное сравнение с референсами, rotation/split-screen и runtime-регресс на физическом устройстве; нативная macOS-сборка подтверждена GitHub Actions. Риск остаётся в фактическом отображении редких content nodes; требуется mixed-channel regression на iPhone/iPad до признания исправления полностью проверенным.

Глобальный поиск статически проверен Swift parser, применением feature overlay к чистому pinned checkout и проверками, что search pipeline использует all-settings model без параметра активной категории. Нативная компиляция успешно прошла; клавиатура/Back, внешний вид тем и нажатия на результаты на устройстве не проверены. Вложенные proxy-результаты открывают существующий Proxy screen; отдельного deep-link к конкретной строке Telegram сейчас нет.

GitHub Actions run `36605440836` для коммита `90e3870` подтвердил доступность repository secrets и дошёл до нативной Swift-компиляции. Он выявил две несовместимости нового list-item поиска с актуальным `ItemListUI`: `ListViewItemNode` требовал явный `layerBacked`, а `ItemListItemNode` — свойство `tag`. После добавления `layerBacked: false` и нейтрального `tag` повторный macOS run `36607225646` для коммита `5d4f073` успешно выполнил upstream-аудит, применение overlay, нативную ARM64-компиляцию, упаковку и upload. Создан артефакт `NagramiX-0.3.9-unsigned-arm64` (73 464 163 байта, artifact id `11053890725`). Автоматическое скачивание артефакта из текущего контейнера блокируется ответом Azure Blob `403 Forbidden`; сам GitHub artifact не просрочен и доступен со страницы run.

Следующий шаг: скачать `NagramiX-0.3.9-unsigned.ipa` из публичного GitHub Release `v0.3.9`, подписать и установить IPA, затем выполнить wide/search regression и deleted-message acceptance из `product/features/deleted-messages.md`: normal/deleted reuse, live delete, custom/empty/64-char label, text/media/album и metadata interactions во всех темах. Успешная компиляция подтверждена, но до device-регресса 0.3.9 не считается stable.


## Итоги физической проверки 0.3.9 и Story blur

Пользователь подтвердил как стабильные и защищённые от неявных изменений следующие code paths: старт круглого видео с задней камеры, подтверждение до просмотра Story, отключение свайпа записи Story, скрытие Stories, ID профиля, дата регистрации, wide channel posts (включая albums 2–10), скрытие вкладок Contacts/Calls, Proxy button и скрытие proxy sponsor channel. Правило закреплено в `AGENTS.md`: менять их поведение, ключи, defaults и UI можно только по будущей задаче, которая явно называет соответствующую функцию.

Единственная продуктовая правка этой сессии находится в presentation layer `NagramiXStoryConfirmationController`. Контроллер по-прежнему получает preview signal из точного `StoryContentItem`: photo использует `.story(... id: item.storyItem.id ...)`, video — poster/thumbnail с тем же story id без запуска playback. Над target preview добавлен штатный `UIVisualEffectView` с `UIBlurEffect(style: .dark)` и интенсивностью `alpha = 0.5`; дополнительный black scrim уменьшен с 0.48 до 0.18, чтобы Story оставалась узнаваемой. Confirmation/cancel callbacks, `nagramiXApprovedStoryId` и `nagramiXCanMarkStoryAsSeen` не менялись.

Полное применение overlay к чистому pinned Telegram-iOS `6ad963e5b62d354da79040f388ae2b9132fb17b8` прошло. Swift parser и структурные assertions подтвердили blur hierarchy, два точных photo/video preview paths и неизменный approval/read-state gate. Нативная macOS ARM64-сборка и визуальная проверка на iPhone для этой presentation-only правки ещё должны быть выполнены.


## Search Bar: локальная правка компоновки

По device-скриншоту установлена точная первопричина внешнего круглого `X`: `NagramiXSettingsSearchItem` создавал штатный `SearchBarNode` с `fieldStyle: .glass`. В Telegram-iOS 12.9.2 активное состояние `.glass` намеренно уменьшает background поля на 52 pt и создаёт отдельный 44 pt `GlassBackgroundView` close control. Поэтому `hasCancelButton = false` не помогал: он управляет другим legacy/modern cancel node, а внешний круг принадлежал glass placeholder infrastructure.

Исправлен только `ios/Sources/SettingsUI/NagramiXSettingsSearchHeader.swift`: поле переведено на штатный `fieldStyle: .modern`, его внешний navigation background отключён, `hasCancelButton` оставлен `false`. В результате стандартный loupe остаётся внутри поля, отдельный glass close view больше не создаётся, поле использует всю parent width со штатными adaptive insets, а штатный `clearButton` появляется внутри справа только для непустого текста. Frame list item, локализованный placeholder, `textUpdated` callback и query synchronization не изменялись. Верхняя navigation/segmented panel и `NagramiXSettingsController` с глобальным индексом не изменялись.

Полный overlay успешно применён к чистому pinned Telegram-iOS `6ad963e5b62d354da79040f388ae2b9132fb17b8`; применённый Swift прошёл parser и structural assertions для `.modern`, отсутствия `.glass`, скрытого external cancel, внутреннего clear и полной parent width. Нативная macOS ARM64-сборка и визуальная проверка на физическом iPhone (Light/Dark/AMOLED/custom, portrait/landscape/iPad/split-screen) ещё не выполнены. Следующий шаг: запустить GitHub Actions build, затем проверить Search Bar на устройстве и подтвердить одинаковую global search выдачу для `Proxy` и `Истории` на всех трёх вкладках.

## Исправления после device-тестирования

Текущая сессия сохранила уже реализованные clean-install defaults: полный первый auth flow начинает с русской `LocalizationSettings`, встроенная `.nightAccent` применяется до загрузки account preferences, а сохранённые пользователем язык и тема не перезаписываются. Эти пути повторно проверены по применённому overlay и не переписывались.

Proxy failover теперь использует выбранные 15/30/60 секунд не только для восстановления исходного proxy, но и для подтверждения настоящего Telegram `.online` после применения кандидата. Ping остаётся лишь предварительной доступностью. Existing generation token, event-driven `connectionStatus`, offline gate и отмена stale callbacks сохранены.

Подтверждённая кодом DNS failure mode состояла в том, что любой DoH timeout/error превращался в terminal signal; `MTTcpConnection` закрывал соединение, и при сохранённом Mullvad provider следующая попытка повторяла тот же путь. Это могло оставить запуск в бесконечном reconnect/offline состоянии. `MTDNS` теперь после ограниченной DoH-попытки асинхронно возвращается к штатному native resolver. Реального crash/ANR stack trace пользователь не предоставил, поэтому утверждать конкретное исключение нельзя; device log остаётся обязательным.

Deleted footer теперь измеряется до фиксации `contentSize`: bubble короткого сообщения расширяется под icon + полный label в пределах штатного `maximumContentWidth`, а более длинный label переносится и увеличивает отдельную footer row. Alpha 0.5, реальный archive attribute, persistent key и штатный `Chat/Context Menu/Delete` не менялись.

Mutual badge больше не использует неточную SF Symbol `person.2.fill`: добавлен template-vector рукопожатия. Он подключён в общей `ContactsPeerItem`, которая обслуживает contact list и recipient/forward picker, и по-прежнему использует реальный `TelegramUser.flags.contains(.mutualContact)` без сети. Состояние пересчитывается из item при каждом bind.

`Select From Author` перепроверен против TelegramEngine: `SearchMessagesState` накапливает и дедуплицирует предыдущие страницы, а callback продолжает запросы до `SearchMessagesResult.completed`; только полный накопленный `result.messages` передаётся selection state. Artificial total limit отсутствует, `MetaDisposable` и generation/chat/thread guards отменяют устаревшие callbacks.

Следующий шаг: выполнить macOS ARM64 build, затем физические acceptance tests языка/темы, Mullvad DNS restart, proxy 15/30/60, 300+ сообщений автора, deleted short-text/long-label и mutual badge в обоих списках. Защищённые wide posts, Story confirmation, camera, profile metadata, tabs и search не изменялись.
