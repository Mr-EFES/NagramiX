# Отправка сохранённых удалённых сообщений

Текущее состояние: включено в проверенный IPA0.5.4/build88, **compile_passed / device_pending**. [Сборка, source SHA и пакет](RELEASE_STATUS.md). Записи о локальных проверках ниже описывают подготовку до этой нативной сборки; физическая проверка остаётся отдельной.

Пользователь сообщил два дефекта в физическом build86: архивное «Переслать без» показывает механику рассылки, а отправка архивной копии может оставаться с часиками. Правка реализована в исходниках: implemented / compile_passed / device_pending. В опубликованном IPA её нет; новую сборку без команды не запускать.

## Диагноз и изменение

copyToSingleRecipient ранее использовал copiesAsNew ветку peerSelected и nagramiXSelectCopyRecipient: это была панель рассылки с лимитом1. Теперь одиночный режим использует native forwarding destination flow: один адресат, полноценный обычный чат, Send/тихо/расписание. Избранное также ждёт явного Send. Проверяются readonly и соответствие threadId при повторном использовании контроллера. Отдельный флаг «Сменить получателя» архивного черновика сохраняет single-recipient intent; классический путь прежний.

Deleted IDs сохраняются только как идентификаторы локального черновика/preview. При отправке ChatControllerNode заменяет архивные .forward на .message из snapshot до очистки ввода и native send. Подписи/Unicode/entities, спойлеры и альбомная группировка сохраняются; hideCaptions применяется. Обычные живые сообщения остаются .forward, без новой серверной семантики.

Forward accessory, native message-options preview, список options и отмена умеют подставлять локальный snapshot, если original отсутствует. Архивный preview показывает исходящее сообщение без archive footer, автора и отметки Incoming. Невозможная опция показать автора архивной копии не предлагается. Read gates исходного readonly preview, отправка реакций и существующие callback ограничители не менялись.

Подтверждённый риск в прежнем коде копирования: standalone архивная media сохраняла cloud identity/reference изображения и дополнительные cloud previews/cover файла, хотя соответствующий оригинал уже удалён. Штатный upload может попытаться повторно использовать cloud reference или загрузить отсутствующую миниатюру. Без журналов конкретного устройства это не доказывает единственную причину всех сетевых зависаний.

Новый NagramiXArchivedMediaCopy подготавливает только архивные исходящие вложения. Основной resource должен иметь полный локальный файл; проверяются regular file, ненулевой размер и declared size LocalFileReference. Полный MediaBox cache допустим как источник, незавершённый cache не используется. Создаётся независимый временный hard link (fallback copyItem), который переживает очистку архива. Native LocalFileReference с uniquely-referenced temporary flag передаёт его обычному uploader, без чтения всего файла в Swift Data.

Новые fileId/imageId в Local namespaces, nil partial/cloud reference, реальные размеры и прежние voice/round/video/MIME attributes. Дополнительные preview representations, video thumbnails и cover добавляются только при наличии полных локальных данных; Cloud альтернативы не передаются. Для фото обязателен самый большой representation, чтобы не отправить tiny thumbnail вместо полного фото. Основное вложение недоступно/ошибка staging → RU/EN alert до enqueue. Уже подготовленные файлы откатываются при ошибке формирования пакета.

«Рассылка» остаётся прежним multiple picker и native commit: направления, темы, платежи, silent/schedule/whenOnline и correlation IDs сохранены. Только snapshot payload теперь использует подготовленные локальные ресурсы. Не заявлять восстановление отсутствующих байтов, исправление сетевой авторизации или проверку доставки по одной компиляции.

## Интеграция и проверки

Durable apply_archived_copy_send_fix в ios/apply_features.py — последний helper после прежних overlays.6 native integrated inputs защищены полными SHA256; все24 anchor/replacement операции планируются в памяти до записи. Изменённые источники: ChatControllerForwardMessages, ChatControllerNode, ChatControllerLoadDisplayNode, ChatMessageActionOptions, ChatInterfaceStateAccessoryPanels, ChatInputMessageAccessoryPanel. Новый helper копируется в существующий TelegramCore Sources/Utils glob.3 localization outputs содержат одно новое RU/EN сообщение об ошибке.

Полный clean proof `/tmp/nagramix-053-archive-copy-final-proof`:439outputs; относительно расширенного baseline438 —429побайтно прежних,9целевых изменений,1новый helper. Storage NagramiXMessageArchive/NagramiXArchivedMediaStore, EnqueueMessage/PendingMessageManager, player/recording paths и подготовленные settings swipes побайтно прежние. Все24 операции обратимы до точных native inputs;6drift и rerun отклонены без записи. Swift grammar7изменённых/новых native sources PASS. Реальный hard-link тест подтвердил сохранение байтов после удаления archive pathname и независимого удаления первой ссылки получателя. RU/EN key unique, Python/metadata/diff проверки PASS.

Проверка `/tmp/nagramix-validate-archive-copy-fix.py`, baseline `/tmp/nagramix-053-archive-copy-baseline`. Native API audit: MediaBox complete-path getter, LocalFileReference/native upload, constructors File/Image, peer selection and forward draft pipeline. Apple SDK отсутствует: новый code typecheck и физическая отправка не выполнены. Сетевой round trip, large-file latency fallback copy, filesystem/data-protection поведение на iOS и UI нужны в следующем пакете.

## Физическая приёмка следующей сборки

- Получить, сохранить и удалить с другого аккаунта текст, фото, файл, voice и round; отдельно одноразовые voice/round с ON архива временных сообщений.
- «Переслать без»: выбрать одного адресата, увидеть реальный preview/содержимое и обычный composer; получатель ничего не получает до Send. Проверить Избранное, другого пользователя, группу/канал и тему форума. Смена адресата остаётся одиночной; Cancel ничего не отправляет.
- «Рассылка»: выбрать1/2/3получателя, отправить один или несколько snapshots/альбом. У каждого новая копия без автора, voice и round сохраняют тип/длительность/воспроизведение. Сравнить скачанные основные bytes; clock исчезает после подтверждённой доставки.
- Отдельно hideCaption, комментарий, Unicode/форматирование, без звука, расписание/whenOnline, платный адресат/отмена платежа, destination topic и mixed live+archived выбор.
- Основной файл недоступен → понятная ошибка без нового зависшего сообщения, draft/выбор остаётся. Отсутствие необязательного thumbnail не блокирует полный файл. После enqueue удалить архив → отправка использует закреплённые bytes.
- Readonly просмотр по аватарке: source read gate и локальные реакции не активируются действиями пересылки; destination доступен для подготовки. Обычные сообщения/Переслать от/архивное воспроизведение/настройки остаются прежними.
- Офлайн→онлайн, фон/холодный старт, получение копии официальным Telegram. Если clock остаётся при доступных локальных bytes, собрать этап upload/RPC и код ошибки без credentials: отдельный сетевой дефект пока не исключён.
