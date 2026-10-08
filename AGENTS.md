# Инструкции для разработки NagramiX

## Актуальные правила пользователя — 2026-10-08

- Единственная рабочая ветка проекта — `main`; прежнее требование работать только в `NagramiX` отменено пользователем.
- Актуальная версия разработки — 0.4.8; сохранять все реализованные функции и защищённые пути ниже.
- Чистая сборка 0.4.8 №79 для физического iPhone успешно завершена, релиз опубликован и IPA проверен. Следующую сборку запускать по отдельной команде; завершённую публикацию не повторять. Описание релиза — краткий русский текст о возможностях, без перечисления технических исправлений. Собирать из новых исходников, не переиздавать прежний IPA. Текущий результат — docs/RELEASE_STATUS.md.
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
- Новые видеоопции: «Видео PiP свайпом» — Прочее, «Воспроизводить видео в фоне» — Функции / Видео; оба ON только при отсутствии ключа, сохранённый OFF не сбрасывать. Пользователь подтвердил звук при сворачивании и блокировке. Использовать штатные AVKit PiP/плеер/аудиосессию; новые settings/search, свайп вверх/вниз и узкая привязка audible gallery к native dropAll скомпилированы в №79, compile_passed/device_pending; опубликованный IPA 0.4.8 проверен.
- Настройки Функции / Фотографии и Стикеры и эмодзи: при отсутствии сохранённого значения качество 100%, большие фото ON (предел 2560), размер 100%, время ON. Сохранённые проценты/false не сбрасывать. 100% размера соответствует штатному Telegram; время отключать без потери статусов доставки/реакций. Обычный текст, inline emoji, кубики, видео и файлы сохранять.
- «Компактный список чатов» — Интерфейс / Чаты, default OFF только при отсутствующем ключе. Сохранённый ON/OFF не сбрасывать. По последнему референсу компактный режим уменьшает аватары, размеры текста и отступы только внутри обычной строки списка: 36 / 15 / 14 / 12 пунктов, минимум строки 48 при обычном тексте. Гарнитуры/начертания и цвета штатные, увеличение текста учитывается, OFF возвращает прежние размеры. Предпросмотр/меню, папки и все действия сохранять.
- Текущие задачи для 0.4.8: сохранить подготовленные правки жестов списка чатов/входа через аватарку, архивного воспроизведения и тихой/отложенной отправки; исправлен лишний резерв высоты компактной строки от скрытого индикатора активности. Проверить её плотность по последнему светлому референсу на устройстве. При обоих ON временная полученная копия сохраняется после просмотра/удаления и воспроизводится до очистки архива. Использовать штатные playlist/player, без второго видеоплеера; прозрачность 50% сохранить. Серверную пересылку удалённого ID не имитировать: вариант явной подписи автора ждёт ответа пользователя. Пользователь разрешил чистую сборку 0.4.8 и тестовую публикацию. Изменения прошли нативную компиляцию №79 и включены в опубликованный IPA; физическая проверка ожидается.
- «Опции чатов по тапу» включены при отсутствии ключа. При ON удерживание вне аватарки вызывает штатное меню без предпросмотра, горизонтальные свайпы из любой области, включая оба края и аватарку, переключают доступные папки; боковые действия отключены. При OFF возвращаются штатные свайп-действия. В обоих режимах обычный тап по аватарке открывает полноценный чат с возвратом назад без автоматических отметок прочтения и сброса непрочитанных. Удерживание аватарки сохраняет штатный предпросмотр; короткий тап вне неё — обычное открытие. Сохранить редактирование, права, подтверждения и доступность. Ключ/default/stable IDs и выбор пользователя не менять. Запрет прочтения относится к отдельному экрану, не ко всему аккаунту; обычное открытие не должно переиспользовать такой экран.
- «Временные сообщения»: ключ nagramix.messages.saveTemporaryMessages, default OFF только при отсутствии ключа; сохранённый выбор не сбрасывать. Зависит от «Удалённых сообщений». Полные полученные файлы держать отдельно от очищаемого MediaBox cache; отключение останавливает новое сохранение, существующие копии остаются до явной очистки/локального удаления. Загрузка сама не должна отмечать сообщения просмотренными. Использовать реальные MediaBox/MediaResourceReference APIs pin; поздние callbacks после очистки не должны возвращать файлы. Не обещать восстановление не полученных или уже недоступных байтов.
- «Переслать без»: выбор одиночного адресата сам не отправляет сообщение; использовать существующую панель отправки Telegram с обычным нажатием и меню без звука/по расписанию при удерживании. Не создавать отдельную очередь/таймер и не переносить параметры reply/thread/send-as/платежа исходного чата в копию. Topic/платёж назначения обрабатывает прежний destination commit. Путь штатной пересылки с серверным источником сохранять. Правка прошла нативную компиляцию №79; физическая проверка ожидается, план — docs/COPY_SEND_OPTIONS_FIX.md.
- Оставлен один workflow `.github/workflows/build-unsigned-ipa.yml`, запускаемый вручную. Проверка upstream остаётся шагом сборки.
- Не запускать сборку без отдельной задачи пользователя; APK не относится к этому iOS-проекту.


> **BEFORE MAKING ANY CODE CHANGES, READ THIS FILE AND `docs/AI_HANDOFF.md`.**

## Project identity

- **Name:** NagramiX.
- **Purpose:** an independent, unofficial, modified Telegram client for iPhone/iOS.
- **Base:** an audited pin of the current official Telegram-iOS default branch. At the 2026-09-01 audit it reports iOS 12.9.2. NagramiX is an overlay repository, not a full fork containing the complete upstream source tree.
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
