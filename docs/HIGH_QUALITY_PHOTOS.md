# Фото максимального качества

Пользователь выбрал **обычное фото максимального качества во всех Telegram-клиентах**. Прежний подготовленный вариант image-document с большим превью только в NagramiX заменён. Целевой тип — стандартный TelegramMediaImage / messageMediaPhoto, а не документ. Побайтное сохранение исходного файла, его размера, формата и метаданных не обещается: Telegram обрабатывает обычные фотографии на сервере.

## Настройка

Функции / Фотографии / **«Фото без сжатия»**, native glass, без footer и изменения шрифта; прежняя identity137/position901 сохраняется. Canonical key `nagramix.photos.highQuality`: absent ON, saved OFF/ON сохраняется. Новый ключ имеет приоритет; read-only fallback `nagramix.photos.original` сохраняет выбор подготовленного ранее режима, если такой ключ есть. Старый transport не возобновляется. В предыдущем опубликованном пакете №84 ни одного из этих режимов ещё нет.

ON выбирает JPEG quality100 и native HD cap2560 по большей стороне с aspect-fit без увеличения маленьких фото. OFF возвращает сохранённые ручные проценты и `sendLargePhotos`; они не перезаписываются включением режима. При OFF показываются только ручной процент качества и его заголовок. Отдельный переключатель «Отправлять большие фото» удалён из меню и поиска по запросу пользователя: его предел2560 уже входит в максимум. Сохранённый HD-ключ остаётся для совместимости режима OFF. Остальные разделы, заголовки, IDs, шрифт, поиск и настройки прежние. По прямому запросу пользователя название в UI — «Фото без сжатия» (EN: Photos Without Compression). Это название настройки; технический контракт JPEG100/HD2560 и отсутствие гарантии byte identity остаются прежними.

## Реализация

`apply_gallery_media_modes` — общий guarded адаптер обычных качественных фото и оригинального видео. Полные SHA256 проверяют входы LegacyMediaPickers и FetchPhotoLibraryImageResource после прежних доработок iOS13.0; все уникальные якоря проверяются в памяти до записи обоих файлов. Native video экспорт остаётся в отдельных .inc; photo-document enum/экспорт/Core renderer helper и три renderer/gallery подмены убраны.

В enqueue снимается snapshot выбранного JPEG quality и HD. Rendered UIImage кодируется существующим native progressive JPEG encoder; gallery asset использует стандартный PhotoLibraryMediaResource, теперь с существующим persisted `quality` полем и forceHd. Fetch использует resource quality, поэтому изменение режима/процентов между enqueue, iCloud и перезапуском не меняет уже подготовленные значения. Старые ресурсы с nil quality сохраняют прежний fallback на saved JPEG preference. Postbox resource schema, decoder/encoder/id и APIs не меняются.

Обычное gallery/camera/editor photo остаётся native image media: thumbnail, caption/entities, spoiler, TTL/paid/options/редактор, grouping и downstream upload/cache остаются штатными. Тип photo соответствует стандартным клиентам, а native server ack определяет итоговые размеры/байты. Обычный mixed photo/video альбом больше не разделяется ради photo-document транспорта. Исключение для неподдерживаемого original-video контейнера как документа остаётся в видеофункции.

Явная отправка фото файлом сохраняет исходный file command и стандартное оформление документа. Sticker/GIF/Live Photo video branches, явные width/height/format JPEG/JXL exports, история/аватар/ShareExtension, progressive encoder/cache и video/cloud player не изменяются этой правкой. Фотоистории продолжают использовать сохранённый процент photoQuality прежним путём; chat maximum mode не меняет их байты. Нельзя молча превращать фото в видео или изображение-документ ради превью.

## Проверка

**implemented / compile_pending / device_pending**. Native typecheck/build и фактическая отправка/серверная обработка на iPhone ещё не проверены. Опубликованный0.5.3/build84 эту доработку не содержит. Новый IPA/commit не создавался.

Приёмка:

- В обеих позициях режима отдельного переключателя «Отправлять большие фото» нет в списке и поиске. Чистый запуск ON, saved OFF/ON после перезапуска/обновления; legacy false сохраняется, новый ключ имеет приоритет. OFF возвращает ранее сохранённые процент/HD; включение не обнуляет ручные настройки.
- JPEG/PNG/HEIC, portrait/landscape/EXIF rotation, 12/48MP и маленькие фото: JPEG100/HD до2560 без upscale. Открытие/zoom/скачивание в официальных iOS/Android/Desktop/web как обычного фото, после cloud ack и перезапуска, на другом аккаунте.
- Одиночное фото и mixed photo + original MP4/MOV album: порядок/группировка/подпись/спойлер/таймер/paid/quiet/schedule/reply/edit. Фото файлом остаётся документом; у него нет нового специального renderer.
- Изменить режим и проценты после подготовки отправки, дождаться iCloud/перезапуска: новый resource сохраняет JPEG quality/HD момента enqueue. Legacy nil-q/explicit JPEG/JXL paths прежние.
- Явные правки редактора, Live Photo, stories/avatars и предыдущие media edits сохранить. Нехватка места/ошибка кодирования/iCloud/отмена не должны отправлять повреждённый файл; UI errors проверять физически.

Максимум описывает параметры клиента в стандартном поддерживаемом photo-пути. Это не оригинал 48MP и не гарантия отсутствия серверной обработки.
