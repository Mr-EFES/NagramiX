# Текущий контекст NagramiX 0.5.1

## Авторизованная задача: чистая сборка и тестовый релиз

Пользователь запросил 0.5.1 для реального физического iPhone и релиз в GitHub с краткой русской аннотацией по функциям. Подготовлены версия workflow/registry и product/releases/0.5.1.md, актуальные ссылки/документы и план IPHONE_TEST_0.5.1.md. Commit и normal push main, clean workflow, публикация prerelease разрешены этой задачей. Предыдущие releases/tags/assets сохранять. Ветку main, единственный workflow и точные SHA/anchor guards сохранять.

Telegram13.0 / f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838 повторно подтверждён CURRENT; minimum iOS15.0. Чистая нативная сборка №84/run38093344854 из `7b8137a6d68554b1790322f8ab1f03460ff7823c` выполнена успешно: clean_build=true/publish_release=true/prerelease=true/artifact_run_id пустой, оба cache шага skipped. Новый IPA опубликован и независимо проверен. [Релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.1), [workflow](https://github.com/Mr-EFES/NagramiX/actions/runs/38093344854), [полный результат](RELEASE_STATUS.md). Предыдущие releases/tags/assets сохранены. Все изменения ниже включены в новый пакет; compile_passed/device_pending. Документационный checkpoint после сборки не считать собранным source.

## Изменения, включённые в сборку №84

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

## Выполненные проверки

Перед push выполнены Python compile, metadata, RU intro, три audio resource tests и diff check. Полный clean feature proof `/tmp/nagramix-051-full-proof`: 427 outputs. Проверены 140 изменённых/новых Swift-файлов: 134 без grammar errors, у шести ошибки parser совпали с stock и предыдущим proof (современные Swift constructs). Нормализация окончания selection .inc не изменила ни один из 427 собранных файлов. macOS workflow успешно выполнил нативную компиляцию всех исходников.

После публикации новый IPA, provenance и checksum скачаны в `/tmp/nagramix-release-051/`. Независимая проверка `/tmp/nagramix-verify-release-051.py` прошла; результат `VERIFIED-RELEASE.json`. Размер 80 866 565 байт; SHA256 `e7c0ead5c4f8ba7772027a0bf9617d1516c1fbe2ceafa2e7e611b03367dadb23`. Версия 0.5.1/build84; ZIP CRC, шесть ARM64/iOS Mach-O, iOS15+, bundle/background audio, русские и пользовательские RU/EN ресурсы, все 31 мелодия подтверждены. Tag/release target/provenance совпадают с исходным SHA, аннотация совпадает с tracked notes. Устройство ещё не проверено.

## Защищённые прежние функции и следующий шаг

Камера кружков сзади, story confirmation/cancel/seen gate, запрет story camera swipe/скрытие/repost, ID/дата/контакты, wide posts/mosaics, hiddenContacts/Calls, Proxy/sponsor и stock theme/font сохраняются. Archive: независимое хранение полученных media/TTL opt-in, late callbacks/clear guards, alpha0.5, shared decoder одного полного MessageId/fileId/resourceId. JPEG compatibility contract/quality0–100/native legacy72/full-cache decoding и decoder background UUID owners/nativePiP не упрощать.

Публикация проверена; следующий шаг — физический тест пользователя по [плану](IPHONE_TEST_0.5.1.md). Runtime/UI/яркость/звук/network/список зрителей/отсутствие всех crashes не объявлять проверенными по компиляции. IPA unsigned требует внешней подписи SideStore. После текущей задачи новую сборку без новой команды не запускать.
