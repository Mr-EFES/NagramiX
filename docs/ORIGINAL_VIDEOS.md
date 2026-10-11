# Видео без сжатия

Проверка текущего выпуска: **compile_passed / device_pending**, нативная сборка№86 и независимая проверка опубликованного IPA успешны. [Результат и исходный SHA](RELEASE_STATUS.md). Физические сценарии остаются непроверенными.

Пользователь подтвердил reference: **Nagram**, функция для видео; аналогичной реализации для фото он не встречал. Как reference поведения проверен [SendMessagesHelper.java](https://github.com/NextAlone/Nagram/blob/e09f49fa8c2dde6e81cfccd8eea6984d39d2e997/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L11109): `sendMp4DocumentAsVideo` допускает video branch при forceDocument, а преобразование зависит от VideoEditedInfo. Код Android/reference не переносится в NagramiX.

## Настройка и транспорт

Функции / Видео / **«Видео без сжатия»**, glass-переключатель без footer; stable ID138, position116. `nagramix.videos.original` отсутствует → ON; сохранённый OFF/ON не сбрасывается при холодном старте. Новый параметр init имеет default true в конце; прежние четыре/пять аргументов, ключи и значения настроек совместимы. Настройка фото независима.

`apply_gallery_media_modes` объединяет интеграцию штатных качественных фото и оригинального видео; проверяет полные SHA256 аудированных LegacyMediaPickers и FetchPhotoLibraryImageResource и все уникальные якоря до записи. Video resource export/streaming/metadata остаются прежними; самостоятельный SSignal→Swift bridge больше не зависит от удалённого original-photo транспорта. Подключаемый Swift-компонент работает с private native picker wrapper, без второго upload manager/player и без изменения Telegram API. Режим и `originalMediaReference` снимаются одним snapshot при начале подготовки отправки.

Обычное неизменённое видео из галереи: PHAssetResource `.fullSizeVideo` либо `.video` → requestData → FileHandle → LocalFileMediaResource/MediaBox. Нет VideoLibrary/AVComposition passthrough, который мог бы незаметно перейти в converter; исходный файл не перекодируется и не remux-ится. Используются имя и MIME фактического Photos resource, размер готового файла, PHAsset pixelWidth/pixelHeight/duration. Отдельно кодируются только thumbnail и выбранная обложка. Сохраняются caption/entities/custom emoji, spoiler, uniqueId и допустимая группировка; downstream reply/thread/send-as/quiet/schedule/upload/error остаются native.

MP4 (`video/mp4`) и MOV (`video/quicktime`) получают стандартный `.Video` attribute. Именно он позволяет штатным клиентам выбирать обычный видеоплеер. Кодек остаётся исходным: совместимость старых клиентов, браузеров, HDR/HEVC/ProRes не гарантируется. Сервер может предоставлять дополнительные версии для воспроизведения; проверка сохранности относится к скачиваемому основному original document resource, а не к автоматически выбранному потоку или thumbnail.

Флаг supportsStreaming ставится только при `moov` до `mdat`: bounded parser читает top-level ISO BMFF заголовки (32/64-bit sizes, zero-sized box, лимит1024) и не загружает payload в RAM. Для остальных файлов флаг не обещает потоковое воспроизведение; оригинал не перестраивается ради fast-start. Полное скачивание перед просмотром может потребоваться.

Неподдерживаемые контейнеры сохраняются исходным документом без fake MP4 MIME/атрибутов и без lossy fallback. Если после подготовки в группе смешались такие документы и обычные видео, группа делится на последовательные серии с сохранением порядка. Обычная video-группа остаётся прежней; обычные photo + video группы не разделяются, потому что фото остаётся photo-медиа.

## Границы

Явная отправка файлом, GIF/Live Photo, rendered/tempFile камера/редактор, высокочастотные/slow-motion assets, timed/view-once/paid media и редактирование прежнего сообщения сохраняют штатную обработку. Реальные crop/rotation/mirror/trim/tools/painting/stickers/GIF-mute/bounce не отменяются ради оригинала. Один quality preset без содержательных правок не включает converter при ON. Отсутствующий native thumbnail также сохраняет прежний путь. Фото, истории, аватары и кружки этой правкой не меняются.

Запись/iCloud/metadata/thumbnail error не отправляет неполный файл. Отмена отменяет Photos request, закрывает writer и удаляет temp; после начала финализации cleanup принадлежит worker. Не обещать успешную отправку или завершённый UX ошибки лишь по исходникам — это часть приёмки на устройстве.

## Проверка

Статус: **implemented / compile_passed / device_pending**. Нативная компиляция№86 пройдена, функция включена в проверенный IPA. Серверный byte/hash round trip на устройстве ещё не проверен.

Приёмка на iPhone:

- Чистый запуск: ON; saved OFF/ON после перезапуска и обновления сохраняется. OFF возвращает прежний native converter. Независимость фото и видеорежима.
- Неизменённые MP4/MOV, landscape/portrait/rotation, короткие/4K/большие, H.264/HEVC/HDR и без звука. Проверить реальные размеры/длительность, отсутствие GIF/round semantics, обложку/спойлер/caption/альбом/quiet/schedule.
- Экспортировать именно выбранный Photos resource, сравнить SHA256 и размер с исходным скачанным файлом после cloud ack, перезапуска и на другом аккаунте. «Сохранить в Фото» может создать новый экспорт; для byte identity нужен файл, а не повторный экспорт/thumbnail/поток другой версии.
- Получить сообщение в официальных Telegram iOS/Android/Desktop и web: обычный player для поддерживаемого контейнера/кодека, скачать основной оригинал и сравнить. Отдельно проверить MOV/HEVC в браузере и старых клиентах; универсальное воспроизведение не объявлять без доказательства.
- Fast-start и moov-at-end, обычные/смешанные albums и редкий unsupported container (document без перекодирования), Secret Chat.
- iCloud, отмена в ходе подготовки, недостаток места/ошибка экспорта, повторный выбор. Обрезка/поворот/рисование/фильтры/стикеры/GIF/slow-motion/таймер/paid продолжают выполнять выбранные действия; Photos/камера/редактор не теряют правки.
