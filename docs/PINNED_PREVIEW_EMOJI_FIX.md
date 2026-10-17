# Пользовательские эмодзи в панели закрепления

После физического теста build94 пользователь показал пять значков ABC вместо пользовательских эмодзи в строке «Закреплённое сообщение». При открытии самого сообщения эмодзи видны. Разрешено исправление исходников; новая IPA не запрошена.

## Причина в закреплённой базе

В Telegram13.0 `descriptionStringForMessage` использует отдельный InstantPage preview для `RichTextMessageAttribute`. Эмодзи такого сообщения находятся в `RichText.textCustomEmoji`, а не обязательно в плоских `textEntitiesAttribute`.

`InstantPagePreviewBuilder` сохраняет ID и alt-текст в атрибуте `instantPagePreviewCustomEmoji`. При отсутствии описания файла в page/associated media он намеренно не добавляет `ChatTextInputAttributes.customEmoji`: запасной текст должен оставаться читаемым. Поэтому в панели видны исходные 🔤/ABC, но `TextNodeWithEntities` не создаёт для них InlineStickerItemLayer и не запускает загрузку. У обычного сообщения другой путь отображения, способный загрузить эти файлы.

Это подтверждённый по исходникам сценарий для rich preview; точный payload канала со скриншота на устройстве здесь не извлекался. Обычные сообщения с entities уже имеют нативный путь загрузки, он сохраняется.

## Изменение

Новый helper в TelegramStringFormatting читает неизвестные ID только из уже сформированного и ограниченного нативным builder превью. Не сканируется целиком длинная страница, не заменяются буквальные ABC/обычные Unicode-эмодзи и не меняются текст сообщения или entities.

Панель запрашивает описания этих файлов через существующий `context.engine.stickers.resolveInlineStickers`. Полученные файлы проверяются по полному MediaId и добавляются только в локальную attributed copy. После этого существующие TextNodeWithEntities/InlineStickerItemLayer загружают изображения/анимацию через штатные cache/resource APIs. Известные файлы не требуют дополнительного запроса. До разрешения отсутствующего файла или при пустом/неподходящем ответе сохраняется читаемый alt-текст. Недоступный на сервере или не полученный без сети файл не выдумывается.

Одна панель держит только metadata текущего preview. Смена ID закреплённого сообщения, исчезновение последнего закрепления и смена набора emoji ID отменяют прежний запрос. Ответы проверяют generation и полный MessageId; обработка откладывается на main queue до конца текущего layout. Это защищает от позднего ответа предыдущего закрепления и синхронного cache hit. Повторный layout с тем же набором не создаёт цикл запросов; частичные ответы могут последовательно обновить ещё не известные файлы. При удалении панели disposable освобождается.

После получения файлов вызывается нативный `enqueueTransition` с актуальным сообщением, темой, переводом и геометрией, без анимации смены закрепления. Простого parent requestLayout недостаточно: `LegacyChatHeaderPanelComponent` сравнивает panel identity/interfaceState и может пропустить равное состояние. Прямое обновление текста не сбрасывает ручное раскрытие spoiler dust через полный updateLayout.

Оба обычный и spoiler text node получают ту же дополненную строку. Все исходные диапазоны UTF-16, шрифты, цвета и spoiler-атрибуты сохраняются. Без animationCache/renderer метаданные не запрашиваются и исходный текст остаётся читаемым. Настройки looping/energy saving обслуживаются прежним рендерером. Стиль, высота50pt, thumb, title/count, навигация по закреплениям, unpin/list/context gestures, перевод, screenshot protection и readonly/read-state callbacks не меняются. Новых настроек или ключей нет.

## Проверки

`apply_pinned_preview_emoji` — full-SHA guard нативной панели, семь exact replacements и проверка двух helper destinations/source files до записи. Нативные preview builder, TextNodeWithEntities и EmojiTextAttachmentView не изменены. Зависимости уже есть, Sources/Tests подключаются существующими BUILD glob.

`scripts/validate_pinned_preview_emoji.py --before <baseline> --after <overlay>` проверяет точную область изменения, семь обратных замен и clean/rerun/drift/collision/missing-source сценарии без частичных записей. Native XCTest `NagramiXPinnedPreviewEmojiTests` использует настоящий preview builder: пять неизвестных ABC, partial/mismatched/empty responses, Unicode/spoiler/style, повторяющиеся ID и обычный текст, готовые page media и пустой alt. Тесты включаются существующей целью `//submodules/TelegramStringFormatting:TelegramStringFormattingTests`.

Текущий статус: source_checked / compile_pending / device_pending. На Linux доступны проверки overlay/Python/Swift grammar. Apple SDK compile, native XCTest, сеть аккаунта и UIKit на физическом iPhone здесь не запускались. Исправление отсутствует в ранее выпущенном build94; новая сборка только по новой команде.

Приёмка на iPhone:

1. Войти в канал после очистки media cache и холодного старта, не открывая целевой пост. Проверить загрузку пяти эмодзи именно в панели закрепления.
2. Обычный текст с Unicode/custom emoji, подпись к медиа и rich message; уже кешированные и неизвестные файлы.
3. Быстро переключать закрепления туда/обратно во время загрузки, удалить последний pin/выйти из чата: чужие иконки не появляются, циклов запросов нет.
4. Перевод, изменение закреплённого текста, поворот/ширина, тема, looping OFF/энергосбережение, spoiler reveal. Обновление файлов использует текущее состояние без скачка к другому pin.
5. Проверить обычный чат и просмотр через аватарку, переход по закреплению, список/снятие закрепления и прежние права. При недоступных файлах остаётся читаемый fallback; при повторном входе/переключении выполняется новый штатный запрос.
