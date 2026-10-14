# Таймер перед записью кружка на селфи-камеру

Текущий статус14октября: **compile_passed / device_pending**, правка включена в опубликованный0.5.5/build89. [Пакет и независимые проверки](RELEASE_STATUS.md). XCTest и физическое поведение не проверены. Прежние отметки о подготовке ниже относятся к состоянию до этой сборки.

Статус `source_checked / native_build_pending / device_pending`. Новая сборка не запускалась. [Пользовательский контракт](../product/features/selfie-countdown.md).

## Настройка и UI

`NagramiXTabSettings.selfieCountdown` хранится отдельно под `nagramix.videoMessages.selfieCountdown`, absent/default ON по последнему уточнению пользователя. Сохранённый ON/OFF применяется без миграции или сброса при холодном старте. Stable ID144, Функции/Круглые видео, после выбора задней камеры и перед музыкой; RU/EN title/search, без footer. Прежние идентификаторы и default rear ON сохраняются.

Белый UILabel центрируется в `previewContainerContentView` с тем же круговым clipping, как живой preview. Цифры не добавляются в camera output, MediaEditor entities или video compositor. Изменение цифры объявляется VoiceOver, масштабная анимация отключается при Reduce Motion. Native красный индикатор и автофокус не заменяются новым эффектом или звуком.

## Запуск и отмена

Перед первой записью только при выбранной `.front` и включённой настройке помечается подготовка. Preview уже работает, native focus получает центр кадра. Native `withReadyCamera` остаётся владельцем готовности; трёхсекундный монотонный deadline начинается после готовности preview. Неблокирующий main-queue Timer проверяет остаток каждые50мс, UI меняется только при смене целой цифры. После deadline запускается прежний `camera.startRecording` без второго150мс ожидания. OFF/задняя камера сохраняют штатное ожидание150мс. Live upload получает только путь реально начавшейся записи, приблизительное recordingStartTime переносится к запуску writer.

Native `.holding/.handsFree` сохраняются во время подготовки, поэтому lock жест переводит будущую запись в hands-free без повторного старта. Повторный start не проходит штатный recording guard. Флаг первой попытки не даёт запускать таймер при record-more/resume или flip уже записываемого ролика. Предпочтение rear ON по-прежнему запускает новую запись сразу; для селфи-таймера нужно выбрать переднюю камеру в настройке начальной камеры.

Выход на `.back` через сигнал камеры завершает отсчёт и запускает запись; ready check остаётся прежним. Generation и pending flag проверяются перед timer tick, finish и writer callback; finish сбрасывает pending до запуска, повторное событие не стартует writer второй раз. Cancel инвалидирует generation, timer/position subscription/background observer и убирает цифру. Dismiss всегда вызывает cancel перед остановкой capture; State deinit освобождает ресурсы таймера.

Send/Stop до writer не ждут несуществующий capture result, не ставят `waitingForNextResult` и не создают пустую отправку: завершаются штатным nil completion. При `willResignActive` подготовка отменяется; возврат в foreground не возобновляет запись сам. Restore flash brightness, native stop result/timeout, view-once/send metadata, audio-session mixing/routes и кодеки сохранены.

Готовность preview остаётся штатной: таймер не вводит альтернативную фальшивую готовность или обход разрешений. Длительность первой видимой «3» может быть больше секунды, пока камера готовит первые кадры; после готовности отсчёт длится три секунды. Задержки самой аппаратной камеры и iOS проверяются на устройстве, нулевая системная задержка не обещается.

## Проверки исходников

Последний helper `apply_selfie_countdown` после исправления архивного выделения: один full-SHA input `VideoMessageCameraScreen.swift`, 15 exact anchors до записи; State methods из отдельного `.swift.inc`. Новый compiled source/bundle target не добавляется, существующий NagramiXCore dependency уже присутствует.

Полный overlay на чистом fixture применился. Из463 выходных файлов457 совпали с предыдущим этапом; изменены один native camera файл и пять settings/localization overlay файлов. `scripts/validate_selfie_countdown.py` проверяет scope, точные обратные замены, full-SHA drift и повторное применение без частичной записи, settings default/storage/ID/search, front/rear/OFF branches, timer/cancel/foreground/dismiss cleanup и положение writer/live upload. Audio policy, setupCamera и весь send-body после guard сравниваются побайтно с прежним состоянием.

Повторный полный overlay с чистого fixture совпал463/463 файла с проверенным full-proof. Четыре новых/изменённых Swift исходника прошли grammar parsing без ошибок; Python compile, release metadata и git diff check проходят. Это не Xcode-компиляция и не физический тест: Apple SDK в текущей среде отсутствует. Native сборка по новой команде пользователя, номер следующей рабочей версии0.5.5; опубликованный0.5.4/build88 остаётся прежним.

## Приёмка на iPhone

1. OFF/ON и перезапуск: выбор сохраняется. Rear ON + таймер ON → без цифр. Rear OFF + таймер ON → preview/focus, 3–2–1, duration0 во время подготовки, затем запись; первый кадр/звук файла после countdown, без цифр.
2. Release/cancel на3,2,1 и во время прогрева; повторная запись. Пустой файл, часики отправки, поздний writer и оставшаяся цифра не появляются.
3. Lock до старта и во время отсчёта → hands-free после «1». Flip на заднюю во время отсчёта → запись сразу, без повторного старта. Flip/resume/record-more уже записанного кружка → без нового отсчёта, предыдущий фрагмент сохраняется.
4. Home/lock screen/входящий звонок/закрытие чата во время подготовки → отмена; возврат сам не записывает. Отказ camera/mic permissions → штатная обработка.
5. Music ON/OFF, динамик/AirPods, передняя вспышка, тихая/отложенная отправка, одноразовый кружок, современный/legacy pipeline, светлая/тёмная тема, поворот и VoiceOver/Reduce Motion: native поведение и реальная длительность остаются корректными.
