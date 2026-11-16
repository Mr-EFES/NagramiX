# PiP: три падения0.9.9/build222 и освобождение WebKit на главном потоке

Поздняя стадия105 `web_player_main_queue` следует за `native_pip_refinement`. Она исправляет одну подтверждённую причину всех трёх присланных владельцем падений. Приватные ZIP, исходные отчёты и dSYM в Git не добавлены. Опубликованная IPA222 этого исправления не содержит.

## Подтверждение причины

Все три отчёта относятся к0.9.9/build222. Упали фоновые потоки8,2 и14; последовательность нормализованных адресов одинакова. Это не три различных ошибки формата видео.

Использован оригинальный symbols-артефакт14272933060 из [успешной сборки222](https://github.com/Mr-EFES/NagramiX/actions/runs/43915919721), source/tag7cdc002e1afb6a54867950665f4cda9741aeea88. SHA256 ZIP `f17c6ac01dd3334d9b598243b1c1f934c6d0b598bebcc854efcb6b8814e62f8e` проверен. UUID DWARF TelegramUIFramework `6259A1C8-5375-3724-BC0A-817D597E21C5` точно совпадает с UUID во всех трёх отчётах.

| Смещение TelegramUIFramework | Расшифровка совпадающего стека |
| --- | --- |
|49775568|`NagramiXWebSystemPictureInPicture.dispatch(_:frame:)`, вызов WebKit|
|49776252|`NagramiXWebSystemPictureInPicture.updatePolicy(frame:)`|
|49767988|`NagramiXWebSystemPictureInPicture.stop()`, WebEmbedPlayerNode.swift:421|
|49767296|`WebEmbedPlayerNode.deinit`, WebEmbedPlayerNode.swift:156|
|49768600|ObjC dealloc thunk того же узла|
|49782400|освобождение замыкания|
|49771656|замыкание `WebEmbedPlayerNode.evaluateJavaScript(js:completion:)`|

Ниже находятся SwiftSignalKit и фоновый libdispatch; выше — WebKit/JavaScriptCore. Прежняя реализация удерживала `strongSelf` в рабочей очереди, ожидала WebKit через семафор и могла отпустить последнюю ссылку там же. Деструктор узла синхронно вызывал `stop()` → `updatePolicy()` → `WKWebView.evaluateJavaScript`, что недопустимо вне главного потока. FOUNDATION termination соответствует этому пути. Без подходящих системных символов имена внутренних функций JavaScriptCore не приписываются.

## Исправление

Изменён только `submodules/TelegramUniversalVideoContent/Sources/WebEmbedPlayerNode.swift`.

- Убраны рабочая очередь и блокирующее ожидание семафора. Настоящая последовательная очередь JavaScript работает на main, сохраняет порядок команд и завершений, обрабатывает ошибку, повторный ответ и вложенный enqueue.
- Отложенный вход в очередь захватывает узел слабо. Закрытие отменяет накопленные команды; поздний ответ не запускает следующую команду.
- WebKit, PiP bridge, очередь и observer принадлежат `NagramiXWebPlayerResources`, удерживаемому штатным `QueueLocalObject` из закреплённого Telegram. Его unmanaged reference освобождается именно на main. Простая копия WebKit в async-деструкторе недостаточна: main мог бы выполнить её раньше окончания деструктора на worker.
- Очистка observer/handler/delegate, stop/loading, жестов и последнее освобождение графа выполняются на main. Убран прежний отложенный `debugDescription`.

Сохранены настоящий Gallery/AVKit, общий вход кнопки и свайпа, размеры/поворот видео, WebKit media probe/script, политика ручной паузы и фона, возврат в чат. Нового фильтра соотношения сторон нет. Настройки, строки, UI, кодеки и кружки не менялись; новых app-файлов, зависимостей и потребителей Postbox нет.

## Проверки и границы

`validate_web_player_main_queue.py` исполняет настоящие очередь, владение и enqueue с настоящими `Queue`/`QueueLocalObject`/SignalKit, реальной рабочей Dispatch-очередью и главным RunLoop. Только UIKit/WebKit IO заменены явно обозначенными hosts. В тестовой библиотеке сохранена прежняя адаптация Dispatch-замыканий через WorkItem для Swift6; inline-семантика `Queue.async` не подменена.

Проверяются FIFO, ошибка JS, повторный/поздний ответ, вложенные команды, закрытие в completion, исчезновение узла до queued enqueue и32 освобождения графа без внешней ссылки на WebView. Точный деструктор опубликованной222 воспроизводит обращение к WebKit вне main. Отрицательные изменения проверяют нарушенные порядок, уникальность ответа, отмену и weak ownership. Выполняются debug и `-O`, warnings-as-errors, loader refusals до записи, Swift parse и ранний `canonical_projection`/`CheckCollection`.

`web_player_main_queue` включена в позднюю цепочку и оба обязательных pre-SDK gate. На macOS дополнительно обязателен настоящий iPhoneOS typecheck изменённых методов с UIKit/WebKit и настоящим SignalKit; Linux его не заменяет. Исторические стадии104 и ранее не переписаны. Регрессии104 кнопки/свайпа/переходов/источника/YouTube сохранены и выполнены отдельно.

Полная новая Apple SDK-сборка, live YouTube и физический iPhone после исправления ещё ожидаются. Следующая версия по утверждённой нумерации1.0; новую IPA запускать только по отдельной команде владельца. Проверить горизонтальное, вертикальное, квадратное и нестандартное видео: кнопка и свайп вверх, многократный вход/выход, быстрое закрытие во время запуска PiP, возврат/пауза/блокировка и YouTube. Присланные отчёты доказывают исправляемый вылет WebKit; они не подтверждают аппаратную приёмку всех источников и не доказывают обход серверных/DRM ограничений.

Результаты исходных проверок: [WEB_PLAYER_MAIN_QUEUE_CHECKS.json](WEB_PLAYER_MAIN_QUEUE_CHECKS.json).
