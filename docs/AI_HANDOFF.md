# Текущий контекст NagramiX 0.5.1

## Авторизованная задача: чистая сборка и тестовый релиз

Пользователь запросил 0.5.1 для реального физического iPhone и релиз в GitHub с краткой русской аннотацией по функциям. Подготовлены версия workflow/registry и product/releases/0.5.1.md, актуальные ссылки/документы и план IPHONE_TEST_0.5.1.md. Commit и normal push main, clean workflow, публикация prerelease разрешены этой задачей. Предыдущие releases/tags/assets сохранять. Ветку main, единственный workflow и точные SHA/anchor guards сохранять.

Telegram13.0 / f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838 повторно подтверждён CURRENT; minimum iOS15.0. До нового commit/dispatch новая нативная компиляция не началась. Последний опубликованный пакет принадлежит предыдущему source132ddc364706d63cc31746be343627419c36c85f/run38036214917/№83, не выдавать его за текущий. Публикация 0.5.1 должна использовать новый SHA и новый IPA, artifact_run_id пустой.

## Подготовленные изменения, все включить

- [Отмена первой записи](VOICE_RECORDING_CANCELLATION_FIX.md): cold-start voice/video cancellation и поздние callbacks; сохранить запись вверх и заднюю камеру кружков.
- [Панель выделения](MESSAGE_SELECTION_ACTIONS_FIX.md): delete/export и три способа пересылки; отдельная иконка Groups для массовой рассылки, native single/multi/quiet/schedule.
- [Отложенные реакции](DEFERRED_PREVIEW_REACTIONS.md): account-owned store, JSON вне native pending actions до обычного foreground/read/top/visible открытия, полный MessageId/thread/revision/in-flight и tombstones. Только Reply активирует новый обычный чат; прочие действия не активируют исходный preview. Платные Stars — только обычный путь. Обычный новый выбор отменяет предыдущую запись.
- Начальный in-app playSounds=false только в штатном default, сохранённые codec/preferences остаются. Каталог31 мелодии прежний.
- [Режим истории](../product/features/story-incognito.md): обычный per-story approval/read gate; инкогнито с тем же качественным blurred preview и отдельным подтверждением один раз за viewer. Immutable context mode, отмена, own/live исключения, read guards и предупреждение перед interaction сохранить.
- [Нижние панели выбора](OPTION_SELECTION_SHEETS.md): общий native компонент, заголовок/крестик/описания/отдельная галочка, только Среднее/Максимум и15/30/60 секунд. Закрытие не меняет значение, tap сохраняет.
- [VPN и список прокси](PROXY_VPN_AND_LAYOUT.md): avoidProxyWithVPN absent=false; эвристический detect и effective bypass, saved enabled/server/list/useForCalls остаются; отмена failover/probes, ручные проверки разрешены. Главный блок с условным timeout и VPN → отдельная Check → Share → список. Не обещать универсальное обнаружение VPN или миграцию начатых VoIP.
- [Приветствие](HIDE_GREETING_STICKER.md): hideGreetingSticker absent=true, обычные/business greetings заменены native empty placeholder без preload; явный business editor, служебные состояния и обычные стикеры прежние. ON отменяет preload; OFF fallback при nil.
- [Музыка при записи](RECORDING_WITH_MUSIC.md): единственный native MediaInputSettings.pauseMusicOnRecording_v2 инвертирован, default/missing-field=false; saved0/1 остаются. Не создавать отдельный конкурирующий ключ. Камера/recorder/session остаются штатными, предупреждение про наушники.
- [Последовательное воспроизведение](DISABLE_VOICE_AUTOPLAY.md): disableVoiceAutoplay absent=true, .voice end callback pause+seek0 и return до native loop/next; generation против позднего callback, value-only capture. Music/.file/manual controls/prefetch/read/archive прежние.
- [Новые каналы и время](CHANNEL_MUTE_AND_EXACT_TIME.md): autoMuteNewChannels absent=true, showExactLastSeen absent=false, IDs132–135. Known non-member→member broadcast кроме creator и explicit successful unknown join. Peer+pending forever mute одной транзакцией, сохранить остальные notification fields и manual unmute; first nil→member sync игнорируется. Позднее одобрение unknown private request без peer не охвачено — не обещать. Общий stock presence formatter сохранён; прошлый положительный .present при ON получает местное HH:mm:ss. Hidden/online/OFF прежние; chat/profile observers с lifecycle cleanup.

Все исходные keys/defaults/IDs и сохранённый выбор предыдущих функций остаются. Новые durable файлы — option sheet, deferred reaction store/methods, selection methods и proxy VPN policy. Нативные изменения выражены в ios/apply_features.py; temporary upstream/proof деревья не коммитить.

## Проверки перед публикацией исходников

Последний полный feature proof `/tmp/nagramix-channel-time-proof` на `/tmp/nagramix-channel-time-full-raw`:427 выходов,416 прежние,11 новых относительно предыдущего voice-autoplay proof с6 дополнительными stock inputs;13 обратных substitutions,12 drift+rerun fail closed,9 Swift grammar trees, old RU/EN strings/IDs сохранены. Предыдущие отдельные proofs и контракты в документах выше. Это Linux без Apple SDK: до GitHub Actions новые функции compile_pending/device_pending.

До push выполнить Python compile, metadata, RU intro, git diff --check, tests/test_notification_sound_resources.py; новый полный overlay на clean raw inputs и grammar всех изменённых Swift. Проверить staged paths, не включать секреты/временные логи/IPA. Commit с русским сообщением; normal push main, inspect remote SHA и dispatch inputs.

При ошибке native compilation исправлять узко по точному логу, сохранять защищённые функции и full-hash preflight; повторить чистую сборку новым SHA. После success скачать именно новый IPA/provenance/checksum, validate_unsigned_ipa.py, ZIP CRC/ARM64/minOS/audio/RU/31tones, tag==source, release body==tracked notes. Записать run/build/source/checksum в RELEASE_STATUS.md; обновить registry compile status. Documentation checkpoint не считать собранным source.

Проверки перед commit выполнены: Python compile, metadata, RU intro,3 audio resource tests, diff check. Новый clean feature proof `/tmp/nagramix-051-full-proof` содержит427 outputs. Проверены140 изменённых/новых Swift-файлов:134 без grammar errors, у6 ошибки parser побайтно совпадают с stock и предыдущим proof (современные Swift constructs, включая nonisolated(unsafe)); новых syntax errors нет. Нативный type checking выполняет только macOS workflow.

## Защищённые прежние функции и следующий шаг

Камера кружков сзади, story confirmation/cancel/seen gate, запрет story camera swipe/скрытие/repost, ID/дата/контакты, wide posts/mosaics, hiddenContacts/Calls, Proxy/sponsor и stock theme/font сохраняются. Archive: независимое хранение полученных media/TTL opt-in, late callbacks/clear guards, alpha0.5, shared decoder одного полного MessageId/fileId/resourceId. JPEG compatibility contract/quality0–100/native legacy72/full-cache decoding и decoder background UUID owners/nativePiP не упрощать.

После проверенной публикации следующий шаг — физический тест пользователя по [плану](IPHONE_TEST_0.5.1.md). Runtime/UI/яркость/звук/network/список зрителей/отсутствие всех crashes не объявлять проверенными по компиляции. IPA unsigned требует внешней подписи SideStore. После текущей задачи новую сборку без новой команды не запускать.
