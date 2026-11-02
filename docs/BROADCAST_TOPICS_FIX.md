# Рассылка: все получатели и точная тема назначения

24 октября после IPA123 исправлено открытие отключённой строки форума/сообщества в множественной «Рассылке»: контейнер открывает штатный выбор темы, прежние адресаты сохраняются. **source_checked/native_compile_pending/device_pending**, без новой SDK/IPA. [Причина и проверки](BROADCAST_CONTAINER_SELECTION_FIX.md). Нижние записи относятся к прежним этапам.

Включено в Release0.6.9/build122 на Telegram13.1.1: native_compile_passed/package_verified/device_pending. [Проверенный пакет](RELEASE_STATUS.md). Ниже — исходный контракт и история source-проверок.

22 октября пользователь повторил сбой в опубликованной сборке114: несколько собеседников + рабочая супергруппа + выбранная тема, но видео пришло только в первый чат группы. Предыдущее исправление `transfer_routing` оказалось неполным. Новая правка подготовлена в main: **source_checked / native_compile_pending / device_pending**. В IPA114 её нет; сборка не запускалась.

## Причины

1. У каждой вкладки/папки `ChatListContainerNode` собственный `ChatListNode`. Прежняя синхронизация Контакты ↔ Чаты и однократный `beginSelection` не охватывали замену текущего списка папкой. Getter получателей читает только текущий список и требует не только IDs, но и `selectedPeerMap`. Переключение на новый/кэшированный список могло оставить только последнего добавленного адресата. Прежняя тестовая граница имела единственный список и не воспроизводила такой переход.
2. Копии — новые `.message`. `withUpdatedThreadId` меняет локальное поле, сохраняя пустой `replyToMessageId`. В закреплённой базе `PendingMessageManager` передаёт `topMsgId` обычного сообщения внутри `InputReplyTo`; без reply subject у одиночного медиа он не передаётся. Поэтому локальная тема не гарантировала доставку в неё. Старые тесты проверяли только локальный `threadId`.

## Изменение

- Copy picker включает opt-in `nagramiXPreserveCopyRecipients` у своего контейнера. В единой точке `applyItemNodeAsCurrent` переносится актуальное выделение: editing, IDs, peer map, найденные адресаты и callback счётчика Send. Это работает при нажатии вкладки, свайпе, возврате в кэшированную папку и завершении асинхронной загрузки папки. Снятые отметки не восстанавливаются из старого списка; постороннее состояние целевой папки сохраняется. Другие списки Telegram по умолчанию остаются на прежнем пути.
- В отдельной копии для выбранного форума задаются и `threadId`, и `EngineMessageReplySubject` с peer ID назначения / Cloud / ID корня выбранной темы. Комментарий и каждый элемент альбома получают тот же адрес. Исходный batch не мутируется: личные адресаты и обычные каналы не получают тему форума. Явно выбранная General1 допустима, автоматического выбора General/первой темы нет.
- Monoforum сохраняет штатный 64-битный thread/peer маршрут; он не превращается в 32-битный reply к теме форума. Community выбирает реальный вложенный peer прежним native callback, сам контейнер не отправляется. Проверка отсутствующей темы и snapshot peer→thread остаются до оплаты/асинхронной отправки.

Одиночный composer/Send, own-one-shot ownership/таймеры/ограничения получателей, protected copier/media staging, репост, оплата, quiet/schedule/diversion и механизм native enqueue не переписаны. Новых настроек, зависимостей или persisted форматов нет.

## Проверка и пределы

Новая последняя стадия `ios/broadcast_topics.py`/JSON после `quick_format_expanded`:3 полных SHA256,4 точные замены; все входы/anchors проверяются до первой записи. Предыдущие immutable стадии и SHA цепочка сохранены.

Полный overlay Telegram-iOS13.0 pin f1dd7a2:434 файла, изменены только3 заявленных native файла,431 побайтно прежний. Дополнительный inspected raw `ChatListContainerItemNode.swift` проверен по pinned Git blob SHA и не меняется.

`scripts/validate_broadcast_topics.py` выполняет извлечённые native folder handoff, opt-in property, routing block, snapshot/rejection и настоящие `EnqueueMessage.withUpdatedThreadId/withUpdatedReplyToMessageId`. **107 проверок debug и optimized**, warnings-as-errors: воспроизведение старой потери получателей и отсутствующего reply target, два человека + тема, возврат/снятие отметок/пустой выбор/30 пересозданий папок, count callback, caption/album/comment/attributes preservation, General1/другие темы/Int32max, отсутствие утечки темы другим peer, monoforum64bit и native opt-out. **11 fail-closed** случаев без частичной записи; Swift grammar3 файлов и Python AST проходят.

UIKit, Postbox и сеть являются границами тестов. Это не физическая доставка и не Apple SDK type checking. Проверенные upstream `PendingMessageManager`/`OutgoingReplyPeer` использованы для трассировки формата RPC, не изменены. Proof `/workspace/.codex-validation-nagramix-broadcast-topics/verification-final.json`; полный fixture `native-broadcast-topics-initial`.

После отдельной команды на новую IPA проверить на iPhone: видео/альбом + комментарий → два человека из разных папок + конкретная неглавная тема; все три доставки, отсутствие лишней копии в General; повторить поиск/Контакты/Чаты/свайпы папок, смену темы, снятие всех отметок, quiet/schedule/отмену оплаты и собственные одноразовые записи разрешённым личным адресатам. До этого device_pending.
