# Передача контекста NagramiX

## Текущая база

- Дата: 2026-09-29 (UTC).
- Актуальная версия продукта: **0.3.9**.
- Статус: **кандидат в стабильную базовую версию для device-регресса**.
- Платформа: только iPhone/iOS.

## Состояние репозитория и GitHub

Исторической базой 0.3.9 остаётся линия 0.3.8 из `https://github.com/Mr-EFES/NagramiX`. В активном дереве release-файл, workflow сборки и workflow публикации переведены на 0.3.9.

В GitHub Actions сохранены только три необходимые workflow: аудит upstream pin, сборка неподписанного IPA и публикация релиза. Ветка `work` отправлена в GitHub, открыт PR #15. Первый build run `36140188656` подтвердил наличие `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` и дошёл до нативной Swift-компиляции, но обнаружил несовместимый тип placeholder в новом SearchBar. `NagramiXSettingsSearchHeader` исправлен: `SearchBarNode.placeholderString` теперь получает штатный theme-aware `NSAttributedString`, а не `String`. Повторный run `36142093146` успешно собрал, упаковал и загрузил артефакт `NagramiX-0.3.8-unsigned-arm64` размером 73 456 389 байт.

Для текущего checkout восстановлен remote `origin` на `https://github.com/Mr-EFES/NagramiX.git`. В предыдущей сессии push, создание PR и запуск Actions были фактически проверены, однако credential GitHub CLI не перенесён в текущий контейнер: коммит 0.3.9 пока существует локально и требует повторной device-авторизации либо защищённого `GH_TOKEN` для push и запуска workflow. В `docs/BOOTSTRAP.md` описан безопасный неинтерактивный вариант. Секреты и токены в репозиторий не записывались.

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

Следующий шаг: скачать артефакт `NagramiX-0.3.9-unsigned-arm64` со страницы run `36607225646`, подписать и установить IPA, затем выполнить wide/search regression и deleted-message acceptance из `product/features/deleted-messages.md`: normal/deleted reuse, live delete, custom/empty/64-char label, text/media/album и metadata interactions во всех темах. Успешная компиляция подтверждена, но до device-регресса 0.3.9 не считается stable.
