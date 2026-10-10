- Новые настройки: «Авто-мьют новых каналов» `nagramix.messages.autoMuteNewChannels`, absent ON; «Показывать точное время» `nagramix.profiles.showExactLastSeen`, absent OFF. Сохранённый выбор не сбрасывать. Мьют только новой подтверждённой подписки на broadcast, кроме creator; старые подписки/группы и ручной размьют не менять. Первый nil→member sync не является новым join, explicit successful import обрабатывается отдельно одной peer+pending транзакцией. Не обещать мьют неизвестной приватной заявки при позднем одобрении без peer. Точное время только реального прошлого `.present(timestamp)`, местное HH:mm:ss; скрытую приватность не обходить. Сохранять stock formatter, живое обновление и observer cleanup. [Контракт](docs/CHANNEL_MUTE_AND_EXACT_TIME.md), compile_pending/device_pending, опубликованный №83 прежний, сборка 0.5.1 разрешена.

# Инструкции для разработки NagramiX

- «Отключить автовоспроизведение голосовых»: Функции / СООБЩЕНИЯ, действует на voice и round video в native voice playlist. Новый `nagramix.messages.disableVoiceAutoplay` отсутствует → ON; сохранять последующий OFF/ON. Блокировать auto-next в end callback SharedMediaPlayer только для .voice; музыка/.file/manual next/previous/play/seek и read/archive paths сохраняются. После завершения пауза+seek0 без автозапуска. Поздний callback нового playbackItem защищён поколением, не захватывать player сильной ссылкой. Переходы и зацикливание music/выключенной опции остаются native. Подготовлено после №83, compile_pending/device_pending; новую сборку без команды не запускать.


- «Не останавливать музыку при записи кружка»: Функции / КРУГЛЫЕ ВИДЕО, распространяется также на голосовые. При отсутствии сохранённой настройки ON; пользовательский выбор сохранять. Использовать единственный штатный MediaInputSettings.pauseMusicOnRecording_v2 с обратным значением, без нового конкурирующего UserDefaults ключа. Default и missing-field fallback pause=false; сохранённые0/1, enableRaiseToSpeak, encoder/updater сохранять. Штатная настройка «Приостанавливать музыку при записи» должна отражать обратное значение. Запись/аудиосессии/жесты/камера/звонки остаются native; предупреждение про наушники в пояснении. Подготовлено после №83, compile_pending/device_pending; сборку без команды не запускать.


- «Скрывать приветственный стикер»: Интерфейс / Чаты, default ON только при отсутствии `nagramix.interface.hideGreetingSticker`; сохранённый OFF/ON не сбрасывать. Обычное и business-приветствие пустого личного чата заменять штатным Conversation_EmptyPlaceholder; не создавать greeting renderer и не загружать приветственный стикер. Служебные empty states, сообщения/обычные стикеры и явный редактор business-приветствия сохранять. При переключении отменять greeting preload; OFF возвращает native greeting с fallback при nil preload. Подготовлено после №83, compile_pending/device_pending; новая сборка только по команде.


- Новая явно запрошенная VPN-политика: «Не использовать прокси с VPN» в настройках прокси, absent OFF, сохранённый выбор пользователя не сбрасывать. Обход только эффективного прокси, saved enabled/activeServer/list/useForCalls не менять; при снятии обхода уважать актуальный выбор, включая OFF. При bypass остановить failover/автоматические probes, ручную проверку сохранить. Детектор iOS эвристический, не заявлять универсальное распознавание VPN или миграцию уже начатого VoIP. Главный блок → отдельная «Проверить список прокси» → отдельная «Поделиться списком прокси» → список; задержка только при auto ON. Подготовлено после №83, compile_pending/device_pending; docs/PROXY_VPN_AND_LAYOUT.md. Без новой команды сборку не запускать.


## Актуальные правила пользователя — 2026-10-10

- Для выбора ускорения и задержки прокси пользователь выбрал первый макет: штатная нижняя панель с заголовком, крестиком, пояснением, названиями слева и отдельной галочкой справа. Общий компонент, сохранение по тапу строки; закрытие/свайп не изменяют настройку. Только Среднее/Максимум и 15/30/60 секунд. Штатные theme/font/анимации/scroll, перенос длинного текста, VoiceOver selected; ключи/defaults/backend не менять. Подготовлено после №83, compile_pending/device_pending, до текущей сборки; docs/OPTION_SELECTION_SHEETS.md.

- Истории: обычный режим сохраняет «Спросить перед просмотром» и per-story approval/read gate. Инкогнито использует тот же качественный preview с лёгким blur, отдельным пояснением и кнопкой «Смотреть инкогнито» один раз за открытие просмотрщика, независимо от обычного чекбокса; при перелистывании достаточно существующего eye.slash. Не показывать следом предупреждение обычного просмотра. Режим брать из неизменяемой политики content context; собственные истории/эфиры исключены из нового экрана. Отмена не открывает историю и не подтверждает режим. Read guards и предупреждение перед ответом/реакцией сохранять. Правка после №83, compile_pending/device_pending.

- «Уведомления → Уведомления в приложении → Звук»: default OFF только при отсутствии сохранённых штатных настроек. Последующий пользовательский ON/OFF сохранять при холодных стартах и обновлениях; вибрацию, текст, имена и системные push-настройки не менять. Подготовлено после №83, compile_pending/device_pending.

- Реакции из полноэкранного readonly-предпросмотра по аватарке сохранять локально до обычного открытия соответствующего чата, включая Back и перезапуск. Только «Ответить» переводит исходный просмотр в новый обычный чат; сохранение, закрепление, удаление и три вида пересылки не активируют его. Не использовать штатную pending reaction до активации; Stars — только обычный платный путь. Новая реализация compile_pending/device_pending, без запуска сборки; docs/DEFERRED_PREVIEW_REACTIONS.md.

- После физического теста 0.5.1 №83 пользователь запросил исправить отмену первой голосовой записи после холодного запуска. Правка подготовлена, compile_pending/device_pending, опубликованный IPA её не содержит. Следующая сборка только по новой команде. См. docs/VOICE_RECORDING_CANCELLATION_FIX.md и текущий раздел handoff; сохранять намеренную блокировку записи вверх и прежний выбор камеры кружков.
- Следующая подготовленная правка: нижняя панель выделения с «Переслать от» / «Переслать без» / «Рассылка» рядом с удалением и штатным экспортом; у рассылки отдельная native Groups иконка в панели и обоих контекстных меню. Existing settings и single/multi/quiet/schedule handlers сохранять. Новая компиляция ожидается, сборку без команды не запускать; docs/MESSAGE_SELECTION_ACTIONS_FIX.md.

- Текущая версия — 0.5.1. Пользователь прямо разрешил новую сборку для физического iPhone и релиз в репозитории с краткой русской аннотацией по функциям. Включить все подготовленные правки, выполнить commit/обычный push main и новый clean workflow с publish_release=true, prerelease=true, без artifact_run_id. Повторно подтвердить Telegram 13.0 / f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838 как CURRENT. Не выдавать прежний IPA №83 за новый; прежние releases/tags/assets сохранить.
- Новые функции до нативной компиляции имеют compile_pending/device_pending. После успешной сборки и независимой проверки нового IPA отметить compile_passed/device_pending; физическую проверку выполняет пользователь. Состояние — docs/RELEASE_STATUS.md.
- Единственная рабочая ветка проекта — main; прежнее требование другой ветки отменено. Описание нового выпуска — краткий русский текст о возможностях. Не запускать новую сборку без новой команды.
- Существующие стабильный и тестовые релизы, теги и файлы сохранять до отдельной команды на удаление. main — единственная ветка, workflow один; git-историю сохранять.
- Перед публикацией выполнить `python3 scripts/validate_release_metadata.py`.
- При каждом изменении версии одновременно актуализировать README, `docs/AI_HANDOFF.md`, `product/releases/`, `product/features/registry.json`, версию workflow и аннотацию GitHub-релиза. В текущих документах описывать только актуальную версию и состояние; историю хранить в Git. Проверять всё отслеживаемое дерево на упоминания иных версий NagramiX и противоречивые сведения о ветках, PR, сборках и проверках.
- Не выдавать существующий IPA за новый без проверки его исходного SHA. Версии Telegram-iOS и других внешних компонентов не являются версиями NagramiX.
- Для новых пользовательских модификаций, которые логично разрешить включать/выключать, добавлять понятную настройку в соответствующую категорию. Не расширять этим правилом текущую задачу на уже существующие функции без запроса пользователя.
- Темы, стандартные экраны оформления, палитры и шрифты должны совпадать с закреплённой базой Telegram без собственных изменений. Актуальное требование: при отсутствии сохранённых настроек выбрать ночной режим «Системная» (.system), ночную тему «Тёмная» (.nightAccent), force=false; дневная тема остаётся stock defaultSettings. Только один раз перед первым UI. Последующие ручные/системные/Auto Night/custom choices не перезаписывать; defaultSettings/палитры не изменять. Допустимы точечные совместимости: выбор доступного варианта той же светлой/тёмной группы при отсутствии точной базы и передача базы предпросмотра в ThemePickerController; также чтение legacy RGB24 accent/outgoingAccent из TelegramThemeSettings: отсутствующий alpha byte становится opaque, RGB и ненулевая ARGB alpha сохраняются. Для этой совместимости — точечные исключения в MakePresentationTheme, ThemeSettingsAccentColorItem и ThemeAccentColorController; дополнительно ThemePickerController сохраняет выбранную базу и использует её для загрузки варианта/обоев. Остальные защищённые stock-файлы остаются побайтно исходными. Принудительная Dark с выключенной автоматикой отменена. Русский — язык первого приветствия, авторизации и приложения после входа; фоновая синхронизация не должна самопроизвольно включать английский. Сохранённые ручные язык/тема не перезаписываются. Доработанные категории NagramiX изолированы от stock-компонентов.
- Экран подтверждения истории: использовать узнаваемый качественный preview с лёгким blur по первому референсу пользователя; не увеличивать мутную tiny thumbnail. Визуальные правки не должны менять confirmation/approval/cancel/seen-state.
- Первый запуск без сохранённых предпочтений: включены скрытие Контактов/Звонков, кнопка прокси/скрытие спонсора, широкие посты, ID/дата/взаимный контакт, «Переслать без»/«Выделить от автора», задняя камера, скрытие историй/запрет свайпа/подтверждение просмотра/репост, подтверждение исходящего звонка. Выключены удалённые сообщения, история правок, Force TCP. Полный контракт — product/SETTINGS.md; сохранённый выбор не сбрасывать.
- Все новые аннотации, отчёты, документация, сообщения коммитов и описания PR — только на русском языке. Английский допустим в коде, внешних API и локализации по назначению.
- Русские названия кнопок/вкладок/действий писать полностью: «Пропущенные», «Изменить», «Разблокировать», «Включить звук» и т. п. Проверять встроенный ресурс и обновляемые русские языковые пакеты; общий реестр — ios/Resources/ru-full-control-labels.json. Для длинных подписей использовать штатное измерение/перенос/прокрутку, не сокращать слова и не менять шрифты/темы.
- Новые видеоопции: «Видео PiP свайпом» — Прочее, «Воспроизводить видео в фоне» — Функции / Видео; оба ON только при отсутствии ключа, сохранённый OFF не сбрасывать. Пользователь подтвердил звук при сворачивании и блокировке. Использовать штатные AVKit PiP/плеер/аудиосессию; исходная реализация settings/search, свайпов и audible gallery/dropAll скомпилирована в №79. Текущая доработка без PiP добавляет независимые UUID-владельцы разрешения native/HLS декодера вне UIKit hierarchy, сочетая их с native/PiP-флагом; изменения разрешения должны быть идемпотентны. Заголовки всех подкатегорий и поиска — верхний регистр. Новая доработка compile_passed/device_pending, в опубликованный IPA №79 не входит; сборка 0.5.1 разрешена пользователем.
- Настройки Функции / Фотографии и Стикеры и эмодзи: при отсутствии сохранённого значения качество 100%, большие фото ON (предел 2560), размер 100%, время ON. Сохранённые проценты/false не сбрасывать. 100% размера соответствует штатному Telegram; время отключать без потери статусов доставки/реакций. Обычный текст, inline emoji, кубики, видео и файлы сохранять. Исходящие фото кодировать native progressive JPEG с выбранным качеством; UIImage.jpegData для полного фото несовместим с progressive cache contract. Полный cached JPEG декодировать целиком, не обрезать по смещениям серверного JPEG. Сохранить native quality 72 для прежних вызовов, HD/размеры/миниатюры/JXL/явные экспорты; ошибки выделения/кодирования/записи не должны отправлять неполный файл. Текущая JPEG-доработка compile_passed/device_pending, сборка 0.5.1 разрешена пользователем.
- «Компактный список чатов» — Интерфейс / Чаты, default OFF только при отсутствующем ключе. Сохранённый ON/OFF не сбрасывать. По последнему референсу компактный режим уменьшает аватары, размеры текста и отступы только внутри обычной строки списка: 36 / 15 / 14 / 12 пунктов, минимум строки 48 при обычном тексте. Гарнитуры/начертания и цвета штатные, увеличение текста учитывается, OFF возвращает прежние размеры. Предпросмотр/меню, папки и все действия сохранять.
- Текущие задачи для 0.5.1: сохранить подготовленные правки жестов списка чатов/входа через аватарку, архивного воспроизведения и тихой/отложенной отправки; исправлен лишний резерв высоты компактной строки от скрытого индикатора активности. Проверить её плотность по последнему светлому референсу на устройстве. При обоих ON временная полученная копия сохраняется после просмотра/удаления и воспроизводится до очистки архива. Использовать штатные playlist/player, без второго видеоплеера; прозрачность 50% сохранить. Серверную пересылку удалённого ID не имитировать: вариант явной подписи автора ждёт ответа пользователя. Пользователь разрешил чистую сборку 0.5.1 и тестовую публикацию. Компиляция №79 подтверждает только прежнюю реализацию; подготовленные доработки скомпилированы в №82 и включены в проверенный IPA; физическая приёмка ожидается.
- «Опции чатов по тапу» включены при отсутствии ключа. При ON удерживание вне аватарки вызывает штатное меню без предпросмотра, горизонтальные свайпы из любой области, включая оба края и аватарку, переключают доступные папки; боковые действия отключены. При OFF возвращаются штатные свайп-действия. В обоих режимах тап и удерживание аватарки открывают полноценный отдельный чат только для просмотра, с возвратом назад, без поля ввода, автоматических отметок прочтения и сброса непрочитанных. Удерживание аватарки не вызывает меню действий. Короткий тап вне неё — обычное открытие. В меню строки доступны штатные «В архив» / «Из архива» по текущему состоянию; ограничения для Избранного и служебного чата Telegram сохраняются. Аннотация опции: «Удерживайте любую область строки, кроме аватарки, для штатного меню действий.» Сохранить редактирование, права, подтверждения и доступность. Ключ/default/stable IDs и выбор пользователя не менять. Запрет прочтения относится к отдельному экрану, не ко всему аккаунту; обычное открытие не должно переиспользовать такой экран.
- «Временные сообщения»: ключ nagramix.messages.saveTemporaryMessages, default OFF только при отсутствии ключа; сохранённый выбор не сбрасывать. Зависит от «Удалённых сообщений». Полные полученные файлы держать отдельно от очищаемого MediaBox cache; отключение останавливает новое сохранение, существующие копии остаются до явной очистки/локального удаления. Загрузка сама не должна отмечать сообщения просмотренными. Использовать реальные MediaBox/MediaResourceReference APIs pin; поздние callbacks после очистки не должны возвращать файлы. Не обещать восстановление не полученных или уже недоступных байтов.
- Контекстное меню: «Переслать от» — прежняя штатная пересылка; «Переслать без» — один адресат и native forward со скрытым автором, подготовка в чате получателя без enqueue при выборе, включая Избранное, с native quiet/schedule. Для удалённых snapshots — copyToSingleRecipient с лимитом 1 и прежней native send panel, без пересылки удалённого server ID. «Рассылка» — прежний copyAsNew с несколькими адресатами и native send controls. Не создавать очередь/таймер, не переносить source reply/thread/send-as/payment в копии; destination topic/payment commit сохранять. Новый переключатель Рассылка независим; absent key наследует прежний showForwardWithoutAuthor (чистая установка true), сохранённые значения не сбрасывать. Старые keys/default/IDs не менять. Текущий split compile_passed/device_pending, в опубликованный IPA №79 не входит.
- Сохранённые удалённые/одноразовые кружки: использовать штатный embedded/shared decoder с одинаковым полным MessageId/fileId/resourceId. Сохранить прозрачность 50%, footer, archive storage/TTL и native copy send. Не оставлять прежнюю движущуюся поверхность при замене строки; новый узел сразу получает текущий imageScale. Архивные внутренние renderer/mask синхронизировать без второй анимации масштаба, внешнюю stock-анимацию сохранять. Poster скрывать только после первого кадра и не возвращать при PiP reset; дополнительный moving thumbnail не создавать. Обычные видео/IDs/controls не менять. Текущая правка compile_passed/device_pending, опубликованный №79 её не содержит; план — docs/ARCHIVED_ROUND_VIDEO_FIX.md.
- Оставлен один workflow `.github/workflows/build-unsigned-ipa.yml`, запускаемый вручную. Проверка upstream остаётся шагом сборки.
- Не запускать сборку без отдельной задачи пользователя; APK не относится к этому iOS-проекту.


> **BEFORE MAKING ANY CODE CHANGES, READ THIS FILE AND `docs/AI_HANDOFF.md`.**

## Project identity

- **Name:** NagramiX.
- **Purpose:** an independent, unofficial, modified Telegram client for iPhone/iOS.
- **Base:** an audited pin of the current official Telegram-iOS default branch. The 2026-10-09 migration uses Telegram-iOS 13.0 at f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838. NagramiX is an overlay repository, not a full fork containing the complete upstream source tree.
- **Platform:** iPhone/iOS is the only supported application platform.
- **Reference project:** NagramX 1258 is used only as a source of product ideas and behavior references. NagramX code must not be compiled into NagramiX.
- **Platform implementation:** NagramiX product behavior is implemented natively in Swift/Objective-C against official Telegram-iOS.
- **Primary technologies:** Swift, Objective-C/Objective-C++, Python, Bash, Bazel/Starlark, Xcode and GitHub Actions.
- **Target:** an unsigned ARM64 IPA for physical iPhone installation after external signing (for example with SideStore).

### Key directories

- `product/` — the platform-neutral source of truth for NagramiX identity, feature specifications, canonical settings, terminology, parity and release scope.
- `ios/` — the authoritative NagramiX overlay, branding, custom sources, configuration template and patch scripts.
- `ios/Sources/NagramiXCore/` — persistent settings and NagramiX localization resources.
- `ios/Sources/SettingsUI/` — NagramiX settings, custom DoH UI and the proxy-screen overlay block.
- `ios/Sources/TelegramCore/` — proxy failover controller integrated into TelegramCore.
- `ios/Sources/MtProtoKit/` — custom DNS/DoH resolver integrated into the pinned MtProtoKit sources.
- `ios/branding/` — primary and alternate application icon sources.
- `ios/apply_overlay.py` — top-level overlay entry point used by CI; generates private build configuration, applies branding and invokes the feature patcher.
- `ios/apply_features.py` — exact-anchor patches against the pinned Telegram-iOS revision. Treat this as a high-risk integration file.
- `scripts/package_unsigned_ipa.sh` — strips temporary signatures/profiles, validates metadata and packages the unsigned IPA.
- `.github/workflows/build-unsigned-ipa.yml` — authoritative macOS/Xcode/Bazel build pipeline.
- `docs/` — bootstrap/release documentation and the current AI handoff.
- `work/`, `.codex-validation-*`, `.codex-tmp-*`, `artifacts/` and `outputs/` — local checkouts, validation copies or build outputs. They are not authoritative source code and must not be edited as a substitute for changing the tracked overlay.

## Repository model

GitHub Actions checks out the pinned Telegram-iOS commit from `ios/upstream.env`, verifies the expected upstream version, then applies the tracked NagramiX overlay to that clean checkout.

Before an iOS build, `scripts/check_upstreams.py --require-current` compares the audited pin and version with the official Telegram-iOS default branch. A stale result blocks the build until a deliberate upstream migration audits the exact anchors. Never silently build a moving branch or blindly update a pin.

Do not make product changes directly inside a temporary Telegram-iOS checkout and assume they are preserved. Every durable NagramiX change must exist in tracked overlay source, a tracked patch operation, build configuration, documentation or Git history.

The exact string anchors in `ios/apply_features.py` intentionally fail when the pinned upstream source no longer matches. Do not weaken those checks or replace them with best-effort patching without a deliberate upstream migration review.

## Working rules

### Protected stable features

The following iPhone behaviors were physically accepted in the previous installed build and are frozen. Do not refactor, rename preference keys, change defaults, move UI, or alter their Telegram integration unless a future user request explicitly names the specific feature to change:

- round videos starting directly on the rear camera;
- per-story confirmation before viewing (including its approval/read-state gate);
- disabling the story-camera recording swipe;
- hiding Stories;
- profile ID display;
- registration-date display;
- wide broadcast-channel posts, including the current single-media and 2–10-item mosaic geometry and the stock layout when disabled;
- hiding the Contacts tab;
- hiding the Calls tab;
- showing the Proxy button;
- hiding the proxy sponsor channel.

Treat an incidental behavioral change to any item above as a regression. Tests, documentation, or a narrowly requested presentation-only adjustment may cover a protected feature without changing its established behavior. For the story confirmation screen specifically, keep the confirmation, cancellation, per-story approval, and seen-state logic unchanged unless explicitly requested; its preview presentation may be changed only when the task expressly asks for that visual change.

Every coding agent must:

1. Read `AGENTS.md` first.
2. Read `docs/AI_HANDOFF.md` next.
3. Run `git status` before making changes.
4. Inspect only the relevant project and pinned-upstream paths needed for the current task.
5. Verify the actual source before assuming names, ownership, lifecycle or architecture.
6. Avoid broad refactoring unless it is directly necessary for the requested change.
7. Preserve behavior outside the current task.
8. Remain compatible with the existing overlay architecture and pinned Telegram-iOS base.
9. Reuse suitable existing abstractions, utilities and components.
10. Avoid parallel or duplicate implementations of existing behavior.
11. Never delete code merely because it appears unused; verify all integration paths first.
12. Analyze backward compatibility before changing APIs, persisted keys, formats, bundle metadata or settings semantics.
13. Do not add dependencies unless the task cannot reasonably be completed with the existing stack.
14. Never commit secrets, tokens, Telegram API credentials, signing material, proxy credentials or private data.
15. Avoid modifying generated, vendored or upstream code unless the integration genuinely requires it; express durable upstream modifications through the overlay.
16. Preserve the style and conventions of the surrounding Telegram/NagramiX code.
17. Run proportionate build, validation, test and lint checks whenever available.
18. If full verification is impossible, record the exact limitation in `docs/AI_HANDOFF.md`.
19. Update `docs/AI_HANDOFF.md` before ending the working session.

> Source code and Git history are authoritative. AI_HANDOFF.md is context, not a replacement for inspecting the actual code.

> Never blindly trust conclusions written by a previous AI agent. Verify material assumptions against the repository before modifying code.

## Git as the source of truth

- Inspect `git status` at the start and end of every session.
- Inspect relevant `git log` and blame/history before large or behavior-sensitive changes.
- Preserve another agent's or the user's uncommitted work. Do not overwrite it, stage it accidentally or reinterpret it without investigation.
- Never use `git reset --hard`, `git clean -fd`, force push or another destructive Git operation without direct user authorization and verified targets.
- Do not revert another agent's change simply because its purpose is unclear. Determine its intent first.
- Keep each completed logical task understandable as a focused diff suitable for a Git checkpoint.
- Do not create commits automatically unless the user or the active workflow explicitly requests a commit.
- Do not stage local validation trees, logs, downloaded artifacts or IPA files.

## Multi-agent conflict prevention

Never assume another AI coding agent has the same chat history or internal context.

Material decisions must be represented in at least one durable, inspectable place: source code, Git history, `AGENTS.md` or `docs/AI_HANDOFF.md`.

No important architecture, compatibility requirement, UX decision, known failure or next step may live only in one agent's chat history.

`AGENTS.md` is for long-lived rules. Current work, short-lived risks and concrete next steps belong in `docs/AI_HANDOFF.md`.

## Build and validation rules

- The authoritative full build is the macOS GitHub Actions workflow in `.github/workflows/build-unsigned-ipa.yml`.
- Do not claim a local Windows environment compiled the iOS application. Windows can run static Python/JSON/XML/diff checks and prepare overlay changes, but the native build requires macOS/Xcode.
- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` must remain GitHub Secrets or temporary environment values. Never write real values into tracked files.
- The generated configuration and fake build-only profiles are temporary. Apple signing secrets and real certificates do not belong in this repository.
- A successful compile proves build compatibility, not runtime correctness. Camera, stories, system icons, networking, proxy failover, clean-install defaults and SideStore installation require honest physical-device validation.
- Preserve the unsigned package checks in `scripts/package_unsigned_ipa.sh`, including removal of `_CodeSignature` and embedded profiles and validation of bundle ID, display name and version.

## AI Session Handoff Protocol

Before ending a working session, every AI agent must:

1. Review `git diff`.
2. Review `git status`.
3. Confirm that temporary, generated, downloaded or accidental files have not entered the intended change set.
4. Run the available checks appropriate to the change.
5. Update `docs/AI_HANDOFF.md`.
6. Record in `docs/AI_HANDOFF.md`:
   - what changed;
   - which files changed;
   - what was verified;
   - what was not verified;
   - known issues or risks;
   - the exact recommended next step.
7. Never state that a feature works unless that behavior was actually verified at the claimed level.
