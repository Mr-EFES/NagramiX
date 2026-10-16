# Вылет полноэкранного видео при повторных поворотах

Предыдущая lifetime-правка скомпилирована в build92. 16октября пользователь подтвердил: на том же видео повторные повороты больше не приводят к вылету. Это физическое подтверждение прежнего сценария, не всех возможных ошибок AVKit. По новому сообщению подготовлена отдельная [правка короткого PiP-свайпа и непрозрачного перехода](PIP_SWIPE_TRANSITION.md): source_checked/native_compile_pending/device_pending. Новая сборка не запускалась.

## Что подтверждено отчётом

Холодный запуск, первый широкий видеопост в канале, открытие полноэкранного плеера и несколько portrait↔landscape переходов заканчиваются выходом на домашний экран iPhone. Отчёт версии0.5.5/build89 показывает EXC_BAD_ACCESS/SIGSEGV/KERN_INVALID_ADDRESS в главном потоке, objc_retain → AVSampleBufferDisplayLayer.avkit_sampleBufferDisplayLayerPlayerController → avkit_videoRectInWindow → AVPictureInPicturePlatformAdapter/Pegasus, во время завершения UIWindow rotation animation.

UUID TelegramUIFramework `cebf66b4-6b9c-3d7f-b03a-83de5a607a4c` совпал с независимо скачанным опубликованным IPA89. Единственный app-frame внутри цепочки уведомлений — NotificationCenterUtils, штатный прокси postNotificationName, а не код ориентации видеоплеера. Это не Swift assertion и не подтверждение ошибки подписи/нехватки памяти. Личность повреждённого внутреннего объекта AVKit и точная причина его повреждения по журналу не установлены; не объявлять найденным конкретный Apple use-after-free без runtime-инструментов.

## Изменение интеграции

До lifetime-правки Native UniversalVideoGalleryItem создавал AVPictureInPictureController из каждого подходящего playback-status callback, даже если пользователь только смотрел видео. Поэтому обычный плеер регистрировал AVKit/Pegasus адаптер, который участвовал в оконных rotation notifications. Предварительная регистрация удалена: PiP создаётся только по штатной кнопке или явному вертикальному свайпу. По последующему уточнению короткого свайпа подготовка начинается после8пунктов явного движения и отменяется при небольшом несостоявшемся жесте; фон остаётся непрозрачным до передачи. Обычные просмотр/status/layout callbacks PiP не создают. Обычные layout/orientation callbacks больше не вызывают подготовку PiP.

Подготовка одного владельца защищена от повторного создания. Владелец явно удерживает исходный AVSampleBufferDisplayLayer, старт проверяет его identity относительно текущего UniversalVideoNode. При освобождении отменяются pending request/timer, выключается automatic-inline, снимается delegate, вызывается stop, public contentSource устанавливается nil, затем освобождаются controller и retained layer. Playback delegate остаётся живым на время отсоединения. Используется публичный AVKit API iOS15+; глобальный notification hook/системные private selectors не изменяются.

Чтобы первый свайп после холодного запуска не закрывал видео лишь из-за асинхронной готовности нового AVKit controller, явный запрос ожидает isPictureInPicturePossible максимум2секунды. Timer50мс на main queue, monotonic deadline, weak captures и UUID request identity, без sleep/синхронного ожидания. Повторный запрос не создаёт вторую попытку. Потеря центральности, замена слоя, фон и deinit отменяют ожидание. Истечение срока возвращает штатный dismiss только для того же ещё открытого центрального item; для кнопки остаётся прежний безопасный no-op. Успешная готовность запускает штатные willBegin/didBegin/didEnd/expand.

Настройки/ключи/defaultON PiP и background video сохранены. Native decoder, geometry, seek/play/pause/rate, HLS, фоновые audio/decoder claims, secret/ad/GIF restrictions и server killswitch прежние. Это исправление конкретного пути регистрации/освобождения PiP, не доказательство устранения любых возможных системных ошибок AVKit.

## Проверки

`apply_video_rotation_pip_lifetime_fix` последним в ios/apply_features.py: один full-SHA guarded native файл, девять точных замен, запись только после всех проверок. Вход SHA `f06ec98b6002eb52386eba27c2e756adcf4675d5ad9d357f1062ac0047412114`. Повторное применение и любой drift отвергаются до записи.

`scripts/validate_video_rotation_pip.py` проверил полный scope460файлов: только UniversalVideoGalleryItem изменён, девять reverse replacements восстановили исходный файл. SHA drift/rerun отказ без частичной записи, отсутствие eager preparation, два явных preparation caller, source identity/cleanup order и pending cancellation guards PASS. Полный чистый overlay совпал со scoped proof460/460. Swift grammar изменённого файла и Pythoncompile/metadata/diff PASS. Apple documentation подтверждает nullable get/set contentSource с iOS15.0.

Нативная компиляция и AVKit/UIKit исполнение в Linux не доступны; XCTest/runtime memory tools не запускались. Изменённый PiP registry имеет compile_pending/device_pending. Не считать статические проверки воспроизведением SIGSEGV на iPhone.

## Физическая приёмка следующей сборки

1. На iPhone17ProMax/iOS27.0 холодный запуск → первый видеопост в канале → fullscreen → минимум20portrait↔landscape переходов, в том числе быстрых, во время playback/paused/buffering. Приложение остаётся открытым, позиция и звук сохраняются.
2. Повторить скачанный MP4 и streaming/HLS, другие чаты/каналы, вход через аватарку, настройки PiP ON/OFF и background ON/OFF. Не менять protected wide-post geometry или read-only preview.
3. Первый явный свайп вверх/вниз и кнопка после холодного запуска: PiP стартует один раз, возврат/закрытие работают. Затем повторить повороты после возвращения из PiP. Если PiP не поддерживается, свайп штатно закрывает галерею, кнопка не запускает недоступную функцию.
4. Свайп и сразу переход на другое видео/закрытие/фон: поздний таймер не запускает старое видео и не закрывает новый экран. Возвращение в приложение и повторное открытие/запуск PiP работают.
5. При новом вылете нужен crash новой версии/build; стек89 не считать подтверждением того, что новая правка была установлена.
