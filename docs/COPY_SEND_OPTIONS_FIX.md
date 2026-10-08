# Тихая и отложенная отправка «Переслать без» для 0.4.8

Состояние: код подготовлен, compile_pending/device_pending. Новая сборка, публикация и смена версии не запускались. Опубликованный IPA №77 этих изменений не содержит.

## Причина

ChatControllerForwardMessages в режиме copyAsNew при одиночном выборе адресата напрямую вызывал multiplePeersSelected(..., .generic, ...). Получатель выбирался, после чего копия немедленно отправлялась. Штатные обработчики .silent/.schedule уже были в общем callback, но пользователь не мог выбрать их на этом пути.

Изучены действительные PeerSelectionControllerParams/protocol, PeerSelectionControllerImpl/Node, ContactListNodeGroupSelectionState, AttachmentTextInputPanelNode, ForwardAccessoryPanelNode, transformEnqueueMessages и EnqueueMessage закреплённого Telegram-iOS. immediatelyActivateMultipleSelection=true здесь не подходит: в этой базе он создаёт PeersCountPanelNode с единственным generic-действием. Для меню вариантов нужен существующий beginSelection с AttachmentTextInputPanelNode.

## Поведение и реализация

«Переслать без» → получатель/тема форума → выбранный адресат отмечается в штатном picker; появляется штатная панель текста и отправки. Обычное нажатие кнопки отправляет сразу; удерживание открывает стандартное меню Telegram с отправкой без звука и по расписанию. Выбор адресата сам не вызывает enqueue. Отмена picker/меню/времени не отправляет копию. Можно дописать комментарий или выбрать несколько получателей.

Durable helper apply_copy_send_options в ios/apply_features.py содержит шесть exact patches для четырёх upstream-файлов:

- AccountContext/Sources/PeerSelectionController.swift: узкий bridge nagramiXSelectCopyRecipient в существующем protocol;
- TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionController.swift: bridge включает штатный beginSelection, возвращает из дочернего picker темы к панели адресата;
- TelegramUI/Components/PeerSelectionController/Sources/PeerSelectionControllerNode.swift: заполняются существующие chat/contacts selection state и foundPeers; Contacts используют реальные ContactListPeerId.peer и ContactListPeer.peer. Кнопка включается по выбранным адресатам, а не по наличию строк в текущем списке. Пустой ForwardAccessoryPanel без исходных ID убирается только на этом пути копирования;
- TelegramUI/Sources/ChatControllerForwardMessages.swift: вместо принудительной .generic выполняется выбор адресата; выбранный mode передаётся штатным обработчикам. Исходные reply/thread/send-as/paid/suggested-post defaults не переносятся в копию при преобразовании тихой/отложенной отправки: из результата native transform берутся только NotificationInfoMessageAttribute и OutgoingScheduleInfoMessageAttribute, остальные исходные поля копии сохраняются. Thread получателя и платежи остаются в прежнем destination commit. Комментарий copyAsNew также не получает thread исходного чата.

Обычная пересылка forwardWithSource сохраняет прежние picker и преобразования. Текст/entities/inline emoji/spoiler, медиа и порядок/группировка копий не менялись. Для архивных копий применяется тот же pipeline; повторно запрашивать удалённый оригинал для пересылки не требуется. Расписание реализует Telegram, отдельного локального таймера/очереди NagramiX нет. Ключ/default видимости действия прежний.

## Проверки

На fresh scoped pin 6ad963e5b62d354da79040f388ae2b9132fb17b8 применён полный overlay. Дополнительные источники selection/panel/contacts сверены по Git blob SHA. По сравнению с baseline уже подготовленных жестов и архивного плеера изменены только четыре generated Swift-файла, 300 остальных совпадают. Все четыре разбираются Swift tree-sitter без ошибок. Отдельный helper совпадает с full overlay; обратное исключение всех шести вставок возвращает четыре файла побайтно.

19 missing/duplicate/already-patched/repeat-helper проверок отклоняют неверные anchors; повторный full overlay также отклоняется. Python syntax, metadata и git diff --check проходят. Native queue/transform/schedule UI не переписаны. В Linux нет Xcode/Swift type checking; UIKit, отмену, доставку и расписание ещё нужно проверить на iPhone. Статическая проверка не подтверждает физическую работу функции.

## План проверки следующего IPA

1. Один получатель, включая Избранное: выбрать «Переслать без» у текста/фото/голосового/кружка/сохранённой удалённой копии. До нажатия кнопки ничего не отправлено. Короткое нажатие — обычная отправка без плашки автора.
2. Удержание кнопки → «Отправить без звука»: сообщение доставлено, получатель не получает звуковое уведомление. Проверять на другом клиенте, а не только по toast отправителя.
3. Удержание → расписание: выбрать будущее время; копия находится в запланированных сообщениях адресата и не приходит сразу, затем доставляется в выбранное время. Проверить комментарий, медиа, сохранённую архивную копию и альбом.
4. Отменить picker, меню отправки и выбор времени: новых/запланированных сообщений нет. Доступность специальных режимов — по штатным ограничениям Telegram.
5. Контакты, глобальный поиск, несколько адресатов, тема форума: сохраняется адресат/его тема; нет reply/thread исходного чата. Проверить повторное открытие, смену папки/фильтра и выбор с пустым текущим списком.
6. Проверить исходный чат с темой/отправкой от имени канала/платной отправкой: параметры исходного чата не применяются к чужому получателю. Платный получатель подтверждается прежним штатным alert; отмена ничего не отправляет.
7. Обычная «Переслать от» для существующего серверного оригинала, OFF/ON видимости «Переслать без», все темы и увеличенный текст сохраняют прежнюю работу. Новые статусы сборки не заявлять до отдельного macOS workflow и проверки IPA.
