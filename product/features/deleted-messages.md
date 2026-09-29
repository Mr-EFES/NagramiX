# Удалённые сообщения

## Состояние и отображение

Источником deleted state остаётся `NagramiXArchivedMessageAttribute`, который ставится только синтетическим display-only сообщениям существующего локального архива. Текст сообщения не используется для определения удаления, backend перехвата delete updates и формат архива не меняются.

Обычные сообщения сохраняют штатный Telegram layout и `alpha = 1.0`. Для архивного сообщения bubble, media/content container, headers, action buttons и reactions получают `alpha = 0.5`; интерактивность и hitboxes не отключаются. При каждом bind alpha назначается явно, поэтому reused cell обычного сообщения возвращается к `1.0`.

Для статуса резервируется отдельная компактная строка внизу bubble. В ней справа отображаются существующая theme-tinted Telegram delete icon и метка вторичным цветом текущей incoming/outgoing message theme. Строка добавляется после основного content layout, поэтому не пересекается с time, views, edited и другими штатными metadata. Сам статус не входит в dimmed content container и остаётся читаемым.

## Пользовательская метка

В разделе «Функции → Сообщения» строка «Текст метки удаления» открывает штатный Telegram alert editor. Значение хранится в `nagramix.messages.deletedMessageLabel`, нормализуется в одну строку, обрезается до 64 символов и сохраняется между запусками. Пустое значение использует локализованный fallback `Удалено` / `Deleted`.

Изменение публикует отдельное notification и перепривязывает сообщения открытого чата без restart. Основной checkbox `nagramix.messages.showDeletedMessages` не меняется: когда функция выключена, архивные сообщения не инжектируются и новый visual state не появляется.

## Проверка на устройстве

- normal/deleted/normal при прокрутке: только deleted имеет alpha 0.5, icon и label;
- live delete в открытом чате обновляет сообщение без повторного открытия;
- custom label, 64-character limit, newline rejection и empty fallback;
- text, photo, video, GIF, file, voice, sticker, forward, reply и grouped media;
- incoming/outgoing в private chat, group, channel и Saved Messages, если snapshot доступен backend;
- Light, Dark, AMOLED и custom themes;
- long press, selection, copy, media viewer, reactions, date/views/edited/footer не ломаются.
