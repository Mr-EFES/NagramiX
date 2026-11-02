# Полные имена в списке реакций/просмотров и при закреплении

Включено в Release0.6.9/build122 на Telegram13.1.1: native_compile_passed/package_verified/device_pending. [Проверенный пакет](RELEASE_STATUS.md). Ниже — исходный контракт и история source-проверок.

22 октября пользователь показал два скриншота IPA114: имя обрезано в меню со списком реакций/просмотров сообщения и в действии «Закрепить у меня и …». Исправление подготовлено в main, **source_checked / native_compile_pending / device_pending**. Новая IPA не запускалась; опубликованная114 этого изменения не содержит.

## Что изменилось

В `ChatControllerLoadDisplayNode` действие личного закрепления использует `EnginePeer.displayTitle` с текущим порядком имени/фамилии и штатный `ContextMenuActionItem.textLayout = .multiline`. Раньше использовались `compactDisplayTitle` и однострочный layout. Шрифт/цвет/ширина и обработчики закрепления/отмены прежние; scope pinAction(true,false) не менялся. «Закрепить у меня», каналы, группы и остальные ветви не переписаны.

В общем `ReactionListContextMenuContent` полное имя уже поступало из displayTitle, но title имел одну строку, а список размещал каждую запись в фиксированных44/56pt. Теперь имя измеряется штатным ImmediateTextNode без ограничения строк/высоты. Для каждого загруженного участника вычисляется высота строки с местом под дату, аватар, статус и реакцию, не меньше прежнего native minimum с учётом listsFontSize. Меню сохраняет свою native ширину260/280pt и шрифты/цвета/отступы. Длинное имя переносится; дата идёт ниже имени.

Рамки строк и полная высота содержимого используют одни prefix offsets. Видимые строки выбираются бинарным поиском по реальным рамкам; заглушки незагруженных участников сохраняют native height, не требуют массива на totalCount и не создают offscreen avatar/emoji nodes. Pagination/loadMore, footer удаления реакции, переходы между вкладками, tap/long tap и engine запросы прежние. Измерения имён кэшируются по полному тексту/доступной ширине/размеру шрифта и очищаются до текущего набора загруженных участников. Прокрутка не измеряет все имена заново.

Место для credibility badge учитывает native EmojiStatusComponent: scam/fake label, emoji, verified и premium. Его расчёт размеров сверен с pinned source; без создания анимированных status views при измерении. Оба пути измерения имени используют общую формулу ширины. Короткие имена сохраняют обычную высоту.

Новых настроек, persisted keys, переводов, шрифтов или зависимостей нет. Full-name удаление, предыдущие post114 изменения рассылки и форматирования сохранены.

## Проверка

Последняя стадия `ios/menu_full_names.py`/JSON после broadcast_topics:2 SHA256,11 exact operations,3 `.inc` templates; все входы/шаблоны/anchors проверяются до записи native файлов. Full overlay pin Telegram-iOS13.0 f1dd7a2 применён:435 файлов, только2 изменены,433 побайтно прежние. Один новый inspected raw компонент проверен по Git blob SHA. Шаблоны вставляются в существующий Swift-файл без BUILD изменений.

`scripts/validate_menu_full_names.py` + `scripts/tests/NagramiXMenuFullNames{Boundary,Tests}.swift`: **9513 проверок в debug и optimized**, warnings-as-errors. Исполняются извлечённые layout/measurement-cache/native pin declaration и прежняя pin declaration для воспроизведения сокращения имени. Проверены полный текст и порядок имени, прежний pin scope, переносимые многострочные размеры, cache invalidation по ширине/шрифту/имени/реакции, badges, Unicode/emoji/RTL/комбинируемые символы, очень длинные имена,90 вариантов списка с разными высотами, overscroll, пустой список, огромный unloaded total. Геометрия бинарного поиска сравнивается с линейным выбором реально пересекающихся рамок.

**22 fail-closed** случая без частичной записи; Swift grammar2 native файлов, Python AST, metadata/diff проверки. Proof `/workspace/.codex-validation-nagramix-menu-fullnames/verification-initial.json`; fixture `native-menu-fullnames-initial`.

UIKit/CoreText и системные размеры шрифтов в Linux тестах представлены управляемыми границами; это проверка source/геометрии, не фактический рендер на iPhone и не Apple SDK type checking. После отдельной команды на IPA проверить оба скриншотных сценария, светлую/тёмную темы, малую ширину/iOS15+, крупный шрифт, листание реакций/просмотров и дозагрузку, verified/premium/emoji status, имена с длинной фамилией и без пробелов, VoiceOver. До этого device_pending.
