# Повторное воспроизведение локальных копий и пересылка

Статус: **source_checked / native_compile_pending / device_pending**. Исправление подготовлено после физического теста0.5.5/build89: повторный запуск архивного кружка даёт артефакты или требует нескольких нажатий; другие сохранённые медиа запускаются не сразу; пересылка медленная. Предыдущие правки поиска и поворотов видео сохранены. Новый IPA не собирался.

## Найденные пути ошибки

- MediaStore возвращал сохранённый полный файл как LocalFileReferenceMediaResource, но не подключал его к complete path MediaBox. Штатный контрол мог показать Remote: первый тап выполнял локальное копирование вместо Play. Native Fetch копировал большой файл через copyItem, даже если полный неизменяемый архив уже находился на том же файловом разделе.
- Архивный кружок выбирал toggle по визуальному FileMediaResourceStatus. Это состояние может отставать от закрытия проигравшего плеера; toggle адресовался уже отсутствующему voice player. У voice тот же статус мог означать только подготовку локального файла.
- Прежняя правка убирала анимации внутреннего renderer, но не сбрасывала его model transform. Повторная передача shared content между overlay и embedded могла сохранить другой масштаб; внешняя поверхность и круглая маска не были заново согласованы при получении ownership. Background/backdrop маски продолжали отдельную анимацию при синхронной внутренней геометрии.
- Native fetchResourceMediaReferenceHash поддерживал VideoLibraryMediaResource, но возвращал nil для архивных исходящих локальных ссылок. Отправленные копии не получали стабильный ключ штатного sent-media cache и повторно загружались.

Это подтверждённые свойства кода, объясняющие возможные дефекты. Реальная доля каждой причины в наблюдённых артефактах/задержке и величина ускорения ещё не измерены на iPhone. Уточняющий вопрос о задержке до выбора адресата или после Send и просмотре через аватарку отправлен; ответа пока нет, он не блокирует общую правку.

## Изменения

MediaStore проверяет, что полный архивный файл существует и имеет сохранённый размер, затем публикует его в штатном cache complete path через hard link. Это не перемещает архив, не читает видео целиком в RAM и не выполняет большой copy на UI-пути. Обрезанная регулярная копия в производном cache path удаляется и восстанавливается из проверенного архива; сам архив не удаляется. Существующий полный кэш используется и отмечается штатным completedResourcePath.

Native Fetch только для источников в nagramix-message-media сначала создаёт hard link. Если prime уже создал тот же inode/device, операция считается завершённой. При невозможности link копирование идёт в соседний временный файл с последующим move: cache complete path появляется только после полного копирования. Ошибка убирает staging file и возвращает false. Все другие fetch/copy/move пути прежние.

Новый public NagramiXArchivedPlaybackAction в AccountContext используется двумя native компонентами. Перед toggle проверяет реальное filteredPlaylistState с account/playlist/item identity. При отсутствии плеера или остановке в конце файла открывается supplied snapshot через прежний callback. Генерация, MetaDisposable/take1/weak captures и валидация текущего account/message/resource препятствуют поздним действиям другой строки. Для voice ветка применяется только к локальным сохранённым ссылкам; incomplete/cloud download/cancel, sending и updating-media пути остаются native. Обычные сообщения и music не меняются. Приватный/readonly open guard не обходится.

Для архивных instant videos сбрасывается внутренний model transform renderer/poster/content container, восстановление embedded ownership снимает старые transform/position/bounds animations и возвращает текущий outer imageScale. Background/backdrop masks для архивного кружка обновляются синхронно. Внешняя stock-анимация, настоящая поверхность decoder, IDs, реальные кадры, прозрачность50% родительского сообщения, метка и отсутствие дополнительного blur сохранены. Ordinary circles идут по прежним веткам.

ArchivedMediaCopy добавляет в имя уникального upload pin небольшой namespaced ключ неизменяемого archive resource ID; новый ключ не является хэшем содержимого или секретом. Native CachedSentMediaReferenceKey принимает Data произвольной длины; ключ ограничен128байтами, temp basename не превышает255. Парсер проверяет temporary resource, prefix, UUID и base64/namespace. Только известный archive directory создаёт этот ключ. Native auxiliary methods передают его штатному sent-media cache: после успешной новой загрузки последующая отправка может использовать полученный серверный document. Удалённая исходная cloud reference не возвращается в copy helper; original metadata/attributes/size, уникальные temporary IDs, hard-link pin и rollback/commit прежние. Secret/TTL/force-refresh/anonymous-sticker ограничения native upload не менялись; истёкшие ссылки обрабатывает штатный pipeline.

Первая отправка ещё не загруженной локальной копии требует передачи байтов. Поэтому скорость обычной серверной пересылки не гарантируется для первой загрузки; concurrent первые адресаты также могут загружать файл до заполнения кэша. Не добавлены очередь рассылки, таймер отправки, фиктивная доставка или обход серверных правил.

## Проверки

apply_archived_replay_and_upload_cache_fix последним:8full-SHA native guards,14exact replacements, новый source helper с collision guard. AccountContext BUILD glob Sources/**/*.swift и зависимости Postbox/TelegramCore проверены по pin. Все guards/anchors/helper bytes читаются до native writes. Два изменённых авторских Core source файла копируются прежними этапами overlay.

scripts/validate_archived_replay.py: scope9changed+1new,14reverse replacements,8SHA drift/rerun/helper collision без частичной записи, исходные metadata/copy rollback/обычные ветки PASS. Реальные FS проверки: shared inode, cache clear без потери архива, archive clear без потери upload pin, полное staged publication, стабильный encoded cache key при разных UUID. Эти тесты проверяют файловые контракты, не запускают Swift helper или AVFoundation.

Полный чистый proof `/workspace/.codex-validation-nagramix-archive-replay/full-proof`:465outputs,455прежних относительно before464,9changed+1new; scoped-final-proof совпал465/465. Swift grammar10changed/new, Pythoncompile/metadata/diff PASS. Apple SDK compile, UIKit/decoder/Photos, offline/replay и cached send delivery на iPhone не выполнялись. Нельзя утверждать, что скорость или исчезновение артефактов уже подтверждены устройством.

## Приёмка следующей сборки

1. Архивные deleted/view-once voice/round/video: cold start → первый тап, пауза/продолжение, конец и повторный запуск минимум10раз, переключение между файлами, скролл за экран/обратно. Проверить обычный чат и readonly просмотр по аватарке.
2. Кружок совпадает с обычным по кругу, ring и масштабу, без второй поверхности, растяжения/призрачного фона. Прозрачность50% и footer сохраняются. Ordinary circles, transcription/expansion, fullscreen/PiP/повороты прежние.
3. Без сети и после очистки обычного медиакэша полный архив воспроизводится. Повреждённый cache размер восстанавливается, архивные файлы не исчезают. Отсутствующие/неполные bytes не выдаются за успешную подготовку или доставку.
4. Первый и повторный copy Send одному адресату/в Избранное/другим получателям: измерить подготовку, upload и подтверждённую доставку отдельно; повторная успешная копия использует native sent cache. Secret chat, schedule/silent/topic/payment/anonymous sticker и mixed live/archive сохраняются.
5. Удалить архив после enqueue: pinned copy доставляется. Отмена подготовки не оставляет uncommitted temporary files; cache clear/фон/перезапуск не дают поздних действий другой строки. Просмотр не активирует read/reaction gate.
