# Исправление rich-черновика после ошибки сборки174

Сборка0.8.8/build174, [run42174985406](https://github.com/Mr-EFES/NagramiX/actions/runs/42174985406), source de0d369c6b0a4349ad04994bafa51af0691353c6/main, завершилась failure6 ноября2026 в08:25UTC. Все156 pre-SDK команд и cold gate прошли. Нативная компиляция началась07:35:57UTC, но TelegramCore не собрался. IPA и release assets не созданы; последним опубликованным выпуском остаётся0.8.7/build173. Собственный draft0.8.8/id436175279 пустой; старые релизы и draft0.8.6 не менялись.

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

Отчёты/журнал: `/tmp/nagramix-build-088/build174.log`, `rich-draft-fix-validation.json`, `rich-draft-fix-guards-final.json`, `rich-draft-final-report.json`, `fixed-composition-hashes.json`. Актуальная полная source tree `/tmp/nagramix-pip-transition/fresh`; pre-post `/tmp/nagramix-pip-transition/incremental`. Предыдущие пять исправлений сохранены. В workflow теперь157 обязательных pre-SDK команд, новая проверка первая; проверки не отключались и предупреждения не ослаблялись.

Нового Apple SDK запуска после174 пока нет, compile/device pending. Для следующей попытки действует сохранённое правило отдельной личной команды владельца. Пока0.8.8 не опубликована, повторная попытка остаётся0.8.8. Не выдавать старый IPA173 за новый и не публиковать пустой draft.
