# Анонимные стикеры и скрытие заблокированных авторов

Обе функции добавлены по референсу пользователя, default ON только при отсутствии сохранённого выбора. UI использует короткие названия без footer: «Анонимные стикеры» в Функции/Стикеры и эмодзи; «Скрывать заблокированных» в Функции/Сообщения. Русская и английская локализации, поисковые синонимы и штатные callbacks; stable ID142/143 без изменения прежних ID. [Стикеры](../product/features/anonymous-stickers.md), [блокировка](../product/features/hide-blocked-messages.md).

## Стикеры

`NagramiXAnonymousStickers.swift` готовит только новые `.message` с распознанным sticker-файлом, исключая custom emoji, rich text и ephemeral/welcome пути. Отдельный LocalFile MediaId сохраняет общий файл исходного пака от перезаписи ответом загрузки. Основной resource остаётся прежним; нет чтения полного файла в RAM или перекодирования WEBP/TGS/WEBM. `.Sticker` сохраняет displayText/mask и получает nil packReference; остальные атрибуты первичного файла сохраняются, дополнительные представления набора не переносятся.

`NagramiXAnonymousStickerMessageAttribute` сохраняет исходный файл/partial reference для загрузки байтов. Регистрируется вместе с остальными типами в штатном AccountManager **до открытия account Postbox**, включая процессы расширений. Обычный outgoing whitelist сохраняет его и в cloud, и в secret. Маркер локальный, не является API entity/attribute. InlineBot/OutgoingChatContextResult снимаются только для этого нового стикера: отправка идёт обычным медиа, без серверной подстановки исходного inline-документа. Original `.forward` остаётся штатной пересылкой.

Public enqueue фиксирует настройку один раз на пакет; подготовка выполняется перед анти-капсом и штатным send. «Подмена профиля» удалена по новой команде пользователя. Уже помеченное сообщение не клонируется повторно, даже при изменении настройки. Reply/thread/grouping/correlation/silent/schedule/payment сохраняются.

В `mediaContentToUpload` помеченный стикер обрабатывается **до CloudDocument shortcut**. Вызов uploadedMediaFileContent получает исходную ссылку для resource fetch и очищенный исходящий файл для API/secret payload; transformOutgoingMessageMedia отключён только для этой ветки. Пропускаются CachedSentMediaReference и preupload document reuse: отдельный multipartUpload использует полные исходные bytes. CacheReferenceKey nil не позволяет записать результат под общим хешем исходного стикера. При OFF без маркера прежние ветки побайтно сохраняются.

Штатный `inputDocumentAttributesFromFileAttributes` не изменён: nil packReference кодируется как `.inputStickerSetEmpty` в documentAttributeSticker. Сохраняются MIME, размеры, sticker emoji, animation/video metadata; secret upload остаётся штатно зашифрованным. Отсутствующий/некорректный source маркера даёт ошибку, а не fallback на старый CloudDocument. Реальное принятие сервером нового документа без пака, tap в других клиентах, доступность исходника при истёкшей file reference и поддержка отдельных видов стикеров в secret chat требуют физической приёмки.

## Заблокированные авторы

`NagramiXBlockedMessageFilter` принадлежит Account, имеет weak registry по ObjectIdentifier(Postbox), отдельную очередь, Atomic snapshot и реактивные revisions. Кэш `nagramix-blocked-authors.json` находится в корне конкретного аккаунта, содержит accountPeerId и authorIds, проверяется по текущему владельцу, пишется атомарно. Повреждённый кэш игнорируется. Удаление переписки/архива/локального кэша Telegram не вызывается.

При подписке истории, включении настройки и возвращении в foreground синхронизируется настоящий `contacts.getBlocked(flags:0)` последовательными страницами по 200. Применяется только завершённый список. Отказ/frozen/пустая непродвигающаяся промежуточная страница сохраняют прежнее состояние. Одновременные подписки используют одну синхронизацию; обычное повторное открытие ограничено 60 секундами, foreground/ON обновляют принудительно. OFF отменяет текущий запрос; поколение защищает от позднего результата отменённой синхронизации.

После успешных штатных block/unblock через профиль и BlockedPeersContext обновляется локальный индекс. Изменение набора через setBlocked применяет только затронутые известные ID после успеха RPC, не считает неполную страницу полным списком. Story-only операции исключены. Серверное updatePeerBlocked обновляет индекс из closure UpdateCachedPeerData при штатном replay после verifyTransaction. Серверные RPC, кэшированные флаги Telegram, права и native ошибки не подменяются.

Локальные/серверные изменения во время пагинации записываются поверх итогового ответа, чтобы старый снимок не отменил новую блокировку или разблокировку. Фильтр не создаёт блокировки самостоятельно. Дополнительная синхронизация не меняет список на сервере.

ChatHistoryListNode наблюдает revisions; ChatHistoryEntriesForView исключает входящее сообщение по фактическому author.id уже **после добавления архивных/временных snapshots**, до построения групп и строк. Исходящие, свои сообщения и автор пересланного оригинала не принимаются за заблокированного отправителя. При OFF возвращается штатный путь отображения. В общем случае данные, read state и unread counts остаются прежними; уведомления и другие экраны не фильтруются этой функцией.

Если обычное пузырьковое окно целиком состоит из скрытых сообщений и есть более старая история, используется штатная Navigation к первой границе с прежним count44. Это пропускает пустое окно без увеличения памяти до размера всей переписки. Проверяются текущая location и актуальный ON; повтор той же границы не запускается, custom sources не переключаются. Полная реакция пагинации/holes/альбомов на устройстве пока не подтверждена.

## Проверки

Статус: **implemented / source_checked / compile_pending / device_pending**. IPA/commit/push не запускались. В Linux нет Swift/Xcode/Apple SDK; нативная сборка и выполнение XCTest не подтверждены.

`apply_anonymous_stickers_and_blocked_filter` — последний этап overlay после анти-капса. Девять полных SHA256 и 19 точных замен; все входы, якоря и отсутствие трёх новых файлов проверяются до первой записи. Изменяемые native пути: Account.swift, AccountManager.swift, EnqueueMessage.swift, PendingMessageUploadedContent.swift, AccountStateManagementUtils.swift, BlockedPeers.swift, BlockedPeersContext.swift, ChatHistoryEntriesForView.swift, ChatHistoryListNode.swift. Полный состав/hash таблиц хранится в patcher.

Полный proof из чистого fixture: `/workspace/.codex-validation-nagramix-private-messages/full-proof`; baseline `/workspace/.codex-validation-nagramix-private-messages/before` — прежние 455 outputs плюс четыре точных upstream файла (AccountManager, upload, BlockedPeers, BlockedPeersContext). Результат: 459 → 462 файла; **445 прежних побайтно совпали, 14 изменены, 3 добавлены**. Прежние auth/author-delete/DNS/recording/анти-капс сохранены, сторонних изменений не обнаружено.

`python scripts/validate_private_messages_overlay.py --before BASELINE --after PROOF` проверяет точную обратимость 19 замен, scope, 9 drift/3 collisions/reapply без partial writes, copy identity, источник upload без cache fallback, прежний API mapper, регистрацию/whitelist маркера, story-only isolation, default/saved keys, уведомление UI, пагинацию и сохранение stable ID. Проверки пройдены.

Swift grammar проверена для девяти native и шести overlay/test файлов: новых диагностик нет. В AccountStateManagementUtils сохраняется одна исходная диагностика parser на прежнем пустом syntax node (row1134); fragment/position идентичны до/после, это не нативная компиляция. Python compile, release metadata и diff checks также проверяются локально.

В `NagramiXPrivateMessagesTests.swift` подготовлены 8 XCTest: primary resource/MIME/metadata трёх видов стикеров, nil pack + native inputStickerSetEmpty, исходный пак без изменения, OFF/обычные файлы/native forward, повтор очереди, Postbox coding и whitelist cloud/secret, реальные incoming authors и приоритет новых block/unblock над старым снимком. XCTest **не запускались**.

## Приёмка iPhone

1. Чистая установка: оба ON. Выключить каждый, перезапустить: сохранённые OFF остаются.
2. WEBP/TGS/WEBM из пака, недавних, избранных и inline: отправить в cloud/secret, проверить на другом официальном клиенте воспроизведение и отсутствие перехода к паку; при OFF новый обычный стикер открывает пак.
3. Очередь offline/повтор/перезапуск/изменение настройки: анонимный стикер сохраняет режим; нет подстановки старого документа при ошибке. Исходный пак в собственном picker не повреждён. Проверить silent/schedule/reply/topic/payment.
4. В группе заблокировать автора через профиль и список, затем разблокировать, повторить из другого клиента. Скрываются его реальные входящие, включая архивные; свои и чужие пересылки остаются. OFF возвращает историю.
5. Проверить список больше 200 заблокированных, участок больше 44 подряд скрытых сообщений, holes, альбомы, topics, preview через аватарку, старую историю и разные аккаунты. Не принимать пустое окно за конец всей переписки.
6. Проверить offline после сохранения кэша, cold start и foreground; отсутствующий первый сетевой ответ не должен очищать известные блокировки.
