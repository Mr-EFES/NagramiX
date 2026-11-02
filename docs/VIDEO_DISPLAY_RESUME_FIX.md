# Чёрное окно PiP после блокировки и продолжения видео

**Состояние выпуска:** правка входит в 0.7.2, сборку 130; нативная компиляция, IPA и символы проверены. Физическая проверка ожидается. [Результат и точный исходник](RELEASE_STATUS.md). Упоминания pending и отсутствия SDK ниже описывают проверки до этого выпуска.

Пользователь сообщил: fullscreen → PiP → Home/блокировка → Pause/Play на экране блокировки → разблокировка/возврат в приложение; звук работает, плавающее окно чёрное. По изображению нельзя определить внутреннее состояние AVKit. Предыдущая WIP-правка `video_rotation_registration` устраняет раннюю регистрацию PiP, а не восстановление renderer, поэтому этот сценарий требует отдельного исправления.

## Подтверждённый дефект исходников

`MediaPlayerNode` умеет flush failed-layer при изменении state/timebase. Но повторяющийся timer ждёт `isReadyForMoreMediaData` до запуска polling и не восстанавливает failed-layer. После блокировки playback state и hierarchy могут не меняться: владелец фонового/PiP воспроизведения остаётся тем же. Получается замкнутое ожидание: failed-layer не ready, timer не вызывает путь восстановления, состояние может больше не обновиться.

[Apple документирует](https://developer.apple.com/documentation/avfoundation/avsamplebufferdisplaylayer/requiresflushtoresumedecoding): при недоступности decoder resources слой может потребовать flush и перейти в failed; для продолжения требуется flush. Ошибка этого пути подтверждена исполнением старого timer с моделью failed/not-ready, но реальное состояние слоя на скриншоте не измерялось.

## Исправление

Финальный `video_display_resume` после `crash_report_bot`: один native файл,6точных операций с входным/выходным SHA и полной проверкой до записи. Ранние canonical stages не меняются.

- Main-only recovery в `updateState`, перед readiness-gate timer и `pollInner`.
- Восстановление только при active-приложении, наличии реального слоя, hierarchy либо действующего background/PiP permission и `status == .failed`/`requiresFlushToResumeDecoding`.
- `flush()`, не `flushAndRemoveImage()`: сохранить тот же объект слоя, control timebase и отображённый кадр. Не пересоздавать AVKit source/controller/плеер, не делать seek/play/pause и не сбрасывать позицию.
- Слабый observer `UIApplication.didBecomeActiveNotification` на main вызывает существующий updateState для подходящего владельца; при deinit observer удаляется.
- Состояние requestFrames остаётся штатным. Пауза не превращается в Play; healthy-слои не сбрасываются. В фоне/неактивном приложении этот новый recovery не пробуждает запрещённый decoder.

Общий renderer используется native-видео и sample-buffer HLS-реализацией. Web/AVPlayerLayer backend не переписывается. Настройки, decoder/audio UUID leases, PiP lifecycle/геометрия/Now Playing/чтения/capture protection прежние; цвет/постер/второй плеер поверх чёрного окна не добавляются.

## Проверки

`validate_video_display_resume.py` исполняет извлечённые production recovery, timer branch и foreground callback с явно обозначенной границей UIKit/AVFoundation, проверяя48сочетаний active/inactive/background, hierarchy/lease, failed/requiresFlush. Lock-pause/resume, paused без forced Play, nil-layer,200повторных healthy callbacks без лишнего flush, сохранение layer identity/timebase/позиции/изображения в модели — debug и `-O` PASS. Старый native timer в обоих режимах воспроизводит постоянное ожидание readiness.

5failclosed (rerun, drift/missing input, неверные output/anchor), обратное восстановление native файла, Swift grammar PASS. Совместно применены все3WIP stages: rotation → crash bot → display resume, сверены6целевых выходных SHA. Эти проверки не исполняют реальный AVKit/decoder и не доказывают восстановление на конкретном iPhone.

Статус **source_checked / native_compile_pending / device_pending**. Опубликованный IPA127 правки не содержит. README/ранние stages/две предыдущие WIP-правки сохранены; SDK/IPA/публикация и commit/push не запускались.

## Приёмка следующей сборки

Повторить сценарий пользователя на Native MP4 и поддерживаемом HLS: PiP → блокировка → пауза/продолжение → Home/разблокировка/возврат, затем Expand и повторные повороты. Проверять несколько циклов, paused/playing/buffering, звук/позицию/живое изображение, смену качества и ролика, закрытие PiP, другие inline-видео, настройки background/PiP ON/OFF. Пауза должна оставаться паузой, здоровый кадр не мигать, новый ролик не затрагиваться старым observer. Физическая проверка iOS15+ и iPhone17ProMax/iOS27 ещё предстоит.
