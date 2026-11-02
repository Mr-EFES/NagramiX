# Оригинальные эмодзи в превью списка чатов

Включено в Release0.6.9/build122 на Telegram13.1.1: native_compile_passed/package_verified/device_pending. [Проверенный пакет](RELEASE_STATUS.md). Ниже — исходный контракт и история source-проверок.

22 октября 2026. Пользователь показал пользовательские эмодзи в сообщении и стандартные 🆕 вместо них в списке чатов. **source_checked / native_compile_pending / device_pending**. Исправление отсутствует в опубликованном IPA 0.6.8/build114; новая сборка не запускалась.

## Найденные пути

Предыдущая доработка `apply_pinned_preview_emoji` относится только к панели закрепления. ChatListUI её не использовал. В закреплённом Telegram13.0 rich preview содержит `instantPagePreviewCustomEmoji` с ID и alt-текстом. Когда файл не включён в associated/page media, builder сохраняет читаемый alt, но не добавляет активный `ChatTextInputAttributes.customEmoji`. Поэтому TextNodeWithEntities не создаёт InlineStickerItemLayer и виден 🆕/ABC. При уже известных файлах и обычных entity-сообщениях другой нативный путь работает — отсюда различие каналов. Фактический серверный payload со скриншота не извлекался; подтверждены эти пути в pinned source.

Дополнительно шесть ветвей media prefix в ChatListItemStrings сбрасывали rich attributes и добавляли prefix к строке без сдвига UTF-16 entities/ranges. Это затрагивало подписи фото, видео, голосовых и файлов, включая соответствующие paid-media ветви. Пересланное сообщение проходит тот же formatter; метаданные автора пересылки сохраняются.

## Исправление

Финальная стадия `ios/chatlist_emoji.py`/JSON после `pip_smooth`:3SHA/11exact operations/1helper copy. Все inputs, anchors, Swift glob и destination проверяются до записи; ранние SHA stages и pinned helper не меняются. В ChatListUI уже есть нужные зависимости и Sources Swift glob, новый BUILD/dependency не нужен.

- Новый `NagramiXChatListPreviewEmoji` использует существующие публичные `nagramiXPinnedPreviewEmojiFileIds` / `nagramiXPinnedPreviewApplyingEmojiFiles`. Собираются только ID из итогового ограниченного preview, не весь документ/история. По одному запросу native engine.resolveInlineStickers на набор неизвестных ID в строке; дедупликация и локальный cache, без polling и глобального растущего кеша.
- Полученные TelegramMediaFile проверяются по полному MediaId, после чего активные атрибуты добавляются только к локальной attributed copy. Штатный TextNodeWithEntities/InlineStickerItemLayer загружает и рисует оригинал. Исходные текст/entities/message/Postbox не переписываются. Буквальные 🆕, ABC, Unicode emoji, известные и специальные custom attributes не подменяются.
- Cache snapshot передаётся в background asyncLayout через native Atomic. setupItem отменяет старый запрос при смене account/full MessageId ещё до фонового layout; generation и текущие IDs отклоняют поздние/повторные/чужие ответы. MetaDisposable освобождается при deinit. Синхронный cache result откладывается до окончания apply.
- Callback обновляет native layout по последним params и только когда params соответствуют текущему item. Если metadata пришли между snapshot и apply, дополнительный coalesced refresh исправляет устаревший layout без нового запроса. Это предотвращает необходимость повторно открывать канал.
- `nagramiXChatListPrependMediaPrefix` сохраняет rich attributes и сдвигает плоские entities/spoiler/custom ranges на фактическую длину prefix в UTF-16. Текст native prefix и сообщения сохраняется. Обычные captions остаются на прежнем entity-renderer пути.

Геометрия списка и compact mode, цвета, шрифты, spoilers, drafts, таймеры/доставка, активность, действия строки, read/privacy и сами сообщения не меняются. Нового checkbox нет; действует в обычном и компактном списке, папках и архивных строках, использующих ChatListItem. Если Telegram не вернул файл, остаётся читаемый fallback; недоступное изображение не выдумывается.

## Проверки и границы

`scripts/validate_chatlist_emoji.py` сравнивает полный overlay:445outputs,2изменённых native файла +1helper,442прочих inputs побайтно прежние. Четыре дополнительных исследованных pinned файла включены в baseline444 для честного сравнения. SHA и операции fail closed:20 отрицательных сценариев, включая каждую anchor, helper collision/missing, drift/missing/reapply; отсутствие частичной записи проверено.

Swift tests исполняют неизменённые production helper/state и прежний pinned helper, а также настоящие pinned Atomic.swift/Disposable.swift (Git blob SHA сверены). Проверяются repeated IDs, точные файлы, обычный 🆕, Unicode surrogate/ZWJ/combining sequences, все4media prefixes, rich/обычные captions, metadata fields, full account/peer/namespace/message identity, sync/late/duplicate callbacks, cache/layout race, отсутствие циклов и cleanup. 164 checks в debug и optimized; точные результаты — `/workspace/.codex-validation-nagramix-chatlist-emoji/verification.json`. Fixture native-chatlist-emoji-final; source grammar трёх Swift-файлов, Python AST/JSON, metadata/diff также проверены.

Attributed runs, Postbox media/IDs, scheduler/engine и UIKit/TextNode renderer в Linux tests — boundaries. Используются реальные NSString UTF-16 lengths и native synchronization. Linux CoreFoundation падает при сравнении соседних пользовательских NSObject attribute values, поэтому тестовая модель runs не является Apple NSAttributedString/UIKit проверкой. На production это ограничение тестовой платформы не переносилось; нативная identity equality изучена в pinned ChatTextInputAttributes. SDK и физический iPhone не проверялись этой задачей, stage/commit/push/Actions/IPA не запускались.

## Приёмка следующей IPA

Канал со скриншота: превью показывает те же оригинальные custom emoji, что открытое сообщение, после загрузки metadata без повторного входа. Проверить холодный и тёплый кеш, rich текст/медиа и обычные entities, пересылку, подписи фото/видео/голосовых/файлов, альбомы, repeated IDs и буквальный 🆕. Быстро сменить последнее сообщение/папку/аккаунт во время загрузки; чужих изображений и layout loops нет. Проверить normal/compact, светлую/тёмную тему, крупный шрифт, drafts, spoilers и ограниченную сеть. Новая IPA — по отдельной команде пользователя.
