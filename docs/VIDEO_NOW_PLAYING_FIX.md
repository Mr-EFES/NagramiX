# Системное управление фоновым видео и PiP

Актуальный результат: включено в опубликованный Release0.7.1/build127, source32f6b5a; чистая Apple SDK-сборка и проверка IPA пройдены, физическая приёмка ожидается. [Итог выпуска](RELEASE_STATUS.md). Описанные ниже pending/запреты запуска относятся к этапу подготовки.

24 октября пользователь показал ожидаемую системную панель плеера на экране блокировки и попросил вернуть паузу/продолжение фонового видео и PiP, затем продолжить Release0.7.1. Это новое явное разрешение после STOP; пользователь повторил «Продолжай сборку и релиз в репозитории».

## Причина и исправление

В текущем MediaManager native Now Playing writer получает только voice/music playlist state и публикует metadata/remote commands лишь для музыки. NagramiX удерживал аудиосессию/декодер фонового видео и самостоятельного PiP, но не передавал их состояние в этот writer. Поэтому воспроизведение могло продолжаться без управления на экране блокировки.

Добавлено временное описание текущего видео в AccountContext.MediaManager: название, native MediaPlayerStatus, признак PiP и weak-node callback управления. Gallery передаёт обычное слышимое native/HLS видео с прежними eligibility-guards, включая paused state для продолжения; backgroundOFF удаляет обычное видео. Secret/Live Photo/animated/неподдерживаемые варианты сохраняют прежнее поведение. Новый player, decoder, audio lease, background assertion или повторный download не создаётся.

Самостоятельный PiP публикует состояние после фактического didStart и далее при изменениях статуса, независимо от обычной background-настройки. Его lease имеет отдельный UUID: уничтожение gallery не убирает PiP-панель. Close/release/deinit удаляют только собственное описание. Оригинальные AVKit lifecycle, audio category, hierarchy leases, ownership, жесты, геометрия, backend и восстановление интерфейса не переписаны.

Единый существующий MediaManager Now Playing writer выбирает источник: переходы фактического native voice/music и видео определяют текущего владельца. Взявшая управление музыка остаётся владельцем после паузы; старый playing-status видео этого не отменяет. Новый owner или новый переход видео в playing возвращает управление ролику. Среди video owners выбирается PiP, затем последний актуальный gallery owner. Status ticks старого owner не перехватывают новый. Перестановка callbacks «video resume»/«music pause» учтена и проверена. Для видео публикуются название/тип/длительность/позиция/скорость, доступны play/pause/toggle и перемотка при конечной положительной длительности. Неопределённые/нечисловые значения очищаются или нормализуются. Next/Previous музыки у видео отключены. Скорость соответствует ролику, paused/buffering останавливает продвижение позиции.

Шесть прежних remote selectors маршрутизируются на главную очередь. Video action обращается к исходному UniversalVideoNode через weak reference. Toggle использует текущий playing/buffering intent, seek ограничивается длительностью. Снимок owner ID не позволяет запоздавшей команде старого плеера управлять новым. При отсутствии video owner остаётся штатный playlistControl. Закрытие видео возвращает native music metadata/controls или очищает панель. Запоздавшие artwork/status музыки не затирают видео. Новый альтернативный MPNowPlayingInfoCenter writer не добавлен.

Настройки/defaultON/background-key и PiP-настройка сохранены, новых checkbox нет. Это управление реальным медиа, не бесконечная фоновая работа приложения и не замена APNs.

## Интеграция и проверки

Финальный video_now_playing после app_icons:3input/outputSHA,28exact ops (одна явно count2 для двух release-сайтов),2BUILDguards,1checked helper-copy. Меняются AccountContext/TelegramUI MediaManager и UniversalVideoGalleryItem; helper registry собирается прежним TelegramUI Source glob. Новых зависимостей нет, Postbox не импортируется. Ранние canonical SHA/13.1port и все предыдущие WIP сохранены.

Proof `/workspace/.codex-validation-nagramix-video-now-playing/{verification,integration}.json`, final native `full-overlay`.96checks debug/optimized исполняют production registry, actual native MediaPlayerStatus/control enums, descriptor, извлечённые MediaManager writer/artwork/status/remote routing. Проверены ownership, PiP priority/transfer/close, paused resume, commands, seek/rate/NaN, музыка, поздние callbacks/owner switch и отсутствие leaked remote targets. MediaPlayer/UIKit/Signal delivery — явные boundary doubles; реальный экран блокировки здесь не исполнялся.

47повреждённых inputs/anchors/outputs/helper/path случаев отклонены без частичных записей.3modified+1added/34481прочих файлов побайтно прежние. Swift parse4 и полный clean overlay+branding с независимым replay проходят. Реальный pinned PostboxImportCheck также PASS.

Попытка124 остановилась до SDK именно этим архитектурным guard: новый Gallery Save helper импортировал Postbox. В этом выпуске helper переведён на уже существующий public EngineRawMessage=Message alias из TelegramCore, прямой импорт удалён. Call sites/identity/сохранение/eligibility не менялись;155protected-story checks debug/O и cold checks повторно PASS. Allowlist/guard не ослаблены.

Статус на подготовке: source_checked/native_compile_pending/device_pending. После SDK/IPA нужна проверка iPhone17ProMax и отдельного iOS15+ устройства: native/HLS видео, Home/блокировка/включение экрана, пауза/продолжение/seek/скорость, PiP start/stop/Expand, закрытие gallery, смена ролика/качества, музыка/voice/наушники и отключение background-настройки. Карточку и фактическое возобновление должен подтвердить физический тест.

Перед следующей SDK попыткой тип потока сверён с pinned SwiftSignalKit: ValuePromise требует Equatable, поэтому для содержащего callback Entry применяется штатный Promise<Entry?>(nil) и set(.single(...)). Тестовый ValuePromise сохраняет этот native generic constraint.96checks debug/O и47guards повторно PASS.126 отменён до выпуска, изменения не выданы за SDK-success.
