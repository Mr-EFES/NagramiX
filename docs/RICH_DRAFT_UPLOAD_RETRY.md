# Повтор загрузки rich-черновика

Действующий контракт синхронизации черновиков в базе1.0. Итоговый SDK/пакет — [отчёт1.0](RELEASE_100_FINAL_CHECKS.md); физическая проверка — [план](DEVICE_CHECK_100.md).

## Причина

`PendingMessages/PendingMessageUploadedContent.swift::uploadedRichMessage` теперь правильно возвращает `PendingMessageUploadError`, чтобы ошибка загрузки вложений не отправляла media-less замену редактируемого сообщения. `RequestEditMessage.swift` уже преобразует этот канал ошибки. Второй потребитель, `State/ManagedSynchronizeChatInputStateOperations.swift:270`, остался с `mapToSignal -> Signal<Void, NoError>`. Настоящий `mapToSignal` требует один тип ошибки с обеих сторон. Xcode выдал `conflicting arguments to generic parameter 'U' ('Signal<Void, NoError>' vs. 'Signal<Void, PendingMessageUploadError>')` в08:02:19UTC; остальные независимые targets продолжали собираться из-за существующего `--continueOnError`.

Предыдущая проверка редактора тестировала загрузчик и редактирование, но не включала второй полный consumer pipeline. Это пропущенная интеграционная граница; фиксация только `RequestEditMessage` была недостаточна.

## Исправление

Новая поздняя стадия `rich_draft_upload_retry` после `pip_transition_geometry`: один exact replacement и27 guards, прежние canonical snapshots не меняются. Перед маппером синхронизации добавлен штатный `retry(0.2, maxDelay: 5.0, onQueue: Queue.concurrentDefaultQueue())` из реального SwiftSignalKit. Он переводит сигнал загрузки в NoError, повышая задержку от0.2 до5секунд и удерживая pending operation до результата. Изменение/замена черновика и остановка аккаунта отменяют подписку и повтор. Стандартный `Network.retryRequest` использует тот же оператор и задержки.

До загрузки полного rich payload сетевой `saveDraft` не вызывается, операция не завершается и локальный черновик/его media needs сохраняются. Не добавлен fallback в nil или текст без вложений. После успеха сохраняются те же rich blocks/media IDs, получатель, reply/thread metadata, suggested post и flags; текст/entities не дублируют rich content. Обычный текст и rich text без медиа используют прежний быстрый путь. Штатная обработка ошибки самого `saveDraft` не изменяется. Общий uploader и редактирование сохраняют прежний строгий error contract; повторы добавлены только к синхронизации черновика.

## Проверка

`scripts/validate_rich_draft_upload_retry.py` использует закреплённые реальные реализации Signal, Subscriber, Atomic, Disposable/MetaDisposable, retry, catch, mapToSignal, switchToLatest, take и mapError. BUILD подтверждает, что тестируется именно библиотека, подключённая TelegramCore. Тестовые границы — планировщик времени и Telegram IO/API values. Оба production consumer pipeline и общий rich uploader извлекаются из актуальных исходников; проверяются все три вхождения `uploadedRichMessage(`, включая определение. Новый consumer без тестовой границы останавливает проверку до SDK.

-18 проверок в debug и18 в `-O`, строгие предупреждения: ошибки/успех/задержки/отмена, удержание операции, отсутствие неполного server draft, payload/metadata, обычный текст и сохранение ошибки редактирования.
-Три отрицательных варианта в каждом режиме: исходный вариант действительно не компилируется с той же ошибкой типов; bare fallback и потеря отмены отвергаются во время исполнения.
-66 fail-closed случаев, полный Swift parse изменённого файла, прежние PiP/editor SHA-unwrap и native PostboxImportCheck. Все615 записей предыдущего final manifest сохранены; новый manifest625 записей добавляет только черновик и реальные SignalKit guards. Полная prefix композиция и независимая pre-post fixture совпадают; новая стадия не пересекается с семью post-port outputs.
