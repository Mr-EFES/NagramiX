# Ссылка на профиль в новых сообщениях

Функция реализована по референсу пользователя, с отдельным штатным экраном настроек. **implemented / compile_pending / device_pending**. Новая сборка и публикация не запускались; версия остаётся NagramiX 0.5.3. [Спецификация](../product/features/profile-link-messages.md).

## Экран и состояние

Функции / Сообщения / «Ссылка на профиль» открывает отдельную страницу: переключатель, краткое описание, блок назначения с именем и отдельной строкой ID, возврат к своему профилю, проверка кнопкой «Открыть профиль». Настройка доступна в поиске по ссылке/профилю/ID. Использованы native ItemListSwitch/Disclosure/Action/Text, systemStyle glass для управляющих строк, стандартные тема/шрифт и AlertScreen с числовой клавиатурой. Stable ID главного пункта136, порядок347; прежние IDs сохраняются.

`nagramix.messages.profileLinkEnabled` отсутствует → false. `nagramix.messages.profileLinkUserId` отсутствует/пуст → профиль текущего отправляющего аккаунта. Непустой ID сохраняется строкой, нормализуется после проверки: ASCII-цифры, положительное Int64 в пределах56-битного native PeerId, без отрицательных ID групп/каналов, ссылок и переполнения. Никакие новые ID не логируются.

Для другого профиля редактор проверяет native EngineData Peer и доступный TelegramUser/personal accessHash. Неизвестный ID не сохраняется: нужно предварительно открыть профиль в этом аккаунте. Ошибка показана понятным текстом, Cancel сохраняет прежний выбор. Кнопка своего профиля сбрасывает только target ID, не включение. Изменения отражаются сразу на детальной и родительской странице; observer, операции проверки и открытия освобождаются с экраном.

## Отправка и совместимость

`apply_profile_link_messages` сверяет полный SHA256 интегрированного EnqueueMessage.swift: `06b68a873785be5ff84d38e524e186313150d5d6cf8456b5f95efe38ffb6c33c`. Единственный точный якорь в public enqueue transaction добавляет policy перед обычной обработкой сообщений. Все новые файлы проверяются на отсутствие до записи; повторное применение, drift и коллизии отклоняются.

Новый `NagramiXProfileLinkedMessages.swift` получает известный доступный user в текущей postbox transaction. Состояние считывается один раз на пакет сообщений. Cloud text/captions получают native TextMention, с associatedPeerIds и штатной API-сериализацией inputMessageEntityMentionName. Простой tg://user URL в cloud не выбран, поскольку native OpenUrl открывает только уже известный локальный peer. В SecretChat stock кодировщик пропускает TextMention, поэтому там добавляется поддерживаемый TextUrl tg://user?id=…; открытие неизвестного получателю ID не гарантировано.

Содержимое текста и другие атрибуты не переписываются. Reply, thread, grouping, correlation, media, caption, silent/scheduled и upload paths сохраняются. Оригинальная .forward, rich text и inline-bot results исключены; отправленная как новая копия без автора проходит общий новый send, сохраняя уже имеющиеся ссылки. Пересылка с автором, welcome automation, server edit, реакции и уже отправленные сообщения не изменяются. При повторе сетевой отправки сущности берутся из сохранённого сообщения, настройка повторно не применяется.

Entity ranges используют UTF-16, включая пары surrogate. Добавленные ссылки разделяются на границах существующего форматирования; Bold/Italic/Underline/Strikethrough/Spoiler/BlockQuote сохраняются. Любые иные существующие сущности, code/pre/custom emoji, автоматически распознаваемые URL/email/phone и @/#/$/bot commands защищены от перенаправления. Некорректные исходные ranges дают исходные entities без изменений. Лимит100 включает прежние и новые entities; прежние не удаляются. Пустой текст/пробелы и media без подписи не получают искусственный текст.

OFF и недоступный target возвращают исходное сообщение. Настройки общие, fallback своего профиля привязан к конкретному accountPeerId; другой ID проверяется заново в каждом отправляющем аккаунте. iOS share extension не синхронизируется с UserDefaults основного приложения этой правкой. Нельзя обещать одинаковую доступность профиля во всех клиентах или обход пользовательской приватности.

## Проверки

Audited pin Telegram13.0 / f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838: native entity API/associated peers, secret-chat сериализация, tg URL opening, ItemListController/Action/Alert contracts проверены по фактическому stock source и Git blob SHA. Полный overlay на чистых входах `/tmp/nagramix-051-profile-links-verified-proof`:432 outputs,423 прежних побайтно против recording-continuity proof,6 целевых изменений и3 новых файла. Один native anchor reverse exact; три копии совпадают с tracked sources. Два drift, три коллизии и rerun отклонены до записи. Семь новых/изменённых Swift grammar деревьев без ошибок. Прежние RU/EN строки, сохранение значений, default OFF, лимит ID и cleanup проверены. Скрипт `/tmp/nagramix-validate-profile-links.py`. Python compile, release metadata, русский intro, три существующих resource tests и git diff check прошли.

В `ios/Tests/TelegramCore/NagramiXProfileLinkedMessagesTests.swift` добавлены8 XCTest сценариев: UTF-16/multiline, вложенность форматирования, сохранение ссылки/code/custom emoji, автоматические URL/mentions, некорректные и surrogate ranges, entity budget/whitespace, OFF/forward, SecretChat URL. Fixture копируется в штатный TelegramCoreTestsLib glob. **XCTest не запускались**: здесь нет Swift/Apple SDK. После macOS overlay можно выполнить `bazel test -c dbg //submodules/TelegramCore:TelegramCoreTests` с настройками закреплённой базы. Нативная компиляция нового кода и физическая проверка пока не выполнены.

## Приёмка после следующей сборки

1. Чистая установка: OFF, «Мой профиль» и корректный ID аккаунта; обычная отправка прежняя. ON → отправить текст и caption фотографии/видео/файла второму аккаунту, открыть профиль нажатием на текст в официальном Telegram.
2. Указать доступный другой user ID, проверить показ имени/ID и «Открыть профиль», отправить текст. Проверить Cancel, пустой ввод, буквы, отрицательный/нулевой/слишком большой ID, неизвестный peer; неверный выбор не сохраняется. «Использовать мой профиль» возвращает fallback без отключения опции.
3. Холодный запуск/обновление сохраняют ON/OFF и ID. Два аккаунта: свой профиль меняется по отправителю, другой ID проверяется в каждом аккаунте; недоступность показана явно и не мешает отправке.
4. Emoji/составные emoji, кириллица, несколько строк; bold/italic/spoiler/quotes; исходные URL, @mentions, #hashtags, email/phone, commands, code/pre, custom emoji и множество entities. Текст и исходные действия сохраняются, новые ссылки не создают ошибок отправки.
5. Silent/scheduled send, reply/topics, captions в album, собственный канал с правом публикации, копия без автора и оригинальная forward. Empty media, voice/round, inline-bot/rich text и старые сообщения не меняются.
6. SecretChat: проверить стандартную tg-ссылку у получателя с известным target; неизвестный target не объявлять поддержанным. Проверить OFF и сетевой повтор без дублирования entities.
7. RU/EN, обе темы, большой шрифт, узкий iPhone, VoiceOver, поиск, клавиатура и возврат из профиля: названия/ID и действия доступны, значение на родительском экране актуально.
