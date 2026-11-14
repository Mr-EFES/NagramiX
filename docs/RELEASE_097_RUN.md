# Версия0.9.7 для iPhone — сборка и публикация завершены

**Результат: SUCCESS, IPA опубликован 14 ноября 2026 в 03:33:15 UTC.** [Релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.9.7) · [Скачать IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.9.7/NagramiX-0.9.7-unsigned.ipa) · [Actions213](https://github.com/Mr-EFES/NagramiX/actions/runs/43535111663) · [Независимая сверка](RELEASE_097_PUBLICATION_CHECKS.json) · [План iPhone](DEVICE_CHECK_097.md). Ниже история попыток; исходный собранный commit d6a808c не меняется документационными публикациями.

**Уточнение владельца после первоначальной подготовки:** разрешены необходимые checked retries до успешного IPA и публикации GitHub Release отMr-EFES. Первоначальный запрет повторов ниже этим сообщением заменён. Каждая попытка — один dispatch точного проверенного commit, без автоматического push trigger; все9прежних релизов сохраняются.

Действующая команда владельца: проверенные исправления и необходимые повторные сборки до успешного IPA и публикации GitHub Release отMr-EFES. Первоначальный запрет повторов отменён последующим уточнением. Один dispatch выбранногоSHA, без дубликатов.

До любых push/dispatch прочитаны инструкции и текущий workflow, полные журналы build201/205/206/207/208, release208 и текущая история202–209; также отменённый191. Последняя успешная полная сборка201 —0.9.5/source7ecb6b3. Native208/source d0f03f9 тоже успешна:10039 actions и IPA созданы, общий run failure относится к отдельному package checker.209 успешно перепроверила артефакт208 без SDK. Ошибки202–204 относятся к macOS Foundation/CoreGraphics test boundary/negative-program и доступности Calendar API на iOS15;205 — optional String в RPC errorDescription;206 — relative header modulemap;207 — ObjC imported initializer label;208 — пропущенное изменение RU-каталога локального чтения. Все исправления уже присутствуют в main; их регрессии сохранены.

В текущем и историческом workflow191 нет concurrency/cancel-in-progress и нет автоматического push trigger.191 сообщает только cancellation в overlay; доступный журнал не раскрывает инициатора, поэтому ручная отмена не объявляется доказанной. Следующий192 создан после окончания191; подтверждения отмены concurrency нет. До dispatch будет проверено отсутствие активных run/дубликата выбранного SHA.

Входные main4ec205c/source73 содержат10 стадий64–73 сверх native208,34 изменённых пути приложения. Их frozen source manifest71354ef15a8208cfc2b4dd026f3cc327b11a2874034bc09d15481fd0cbcae089;43complete fixtures/86debug/optimized,649Swiftparse,73inverse/880paths, members/native strings/strict71×668 пройдены при завершении последней правки. В подготовке исходники приложения не изменены. Новые platform-specific probes остаются обязательными в начале macOS job; Linux результаты не объявляются Apple SDK success.

Добавлен `validate_build_inputs.py`: вызываемые скрипты и точный регистр имён, Python/bash syntax,79SDK plans/73late stages и12submodule locks, прежние bundle/team/release_arm64/unsigned packaging, manual-only/no cancellation. В CI также требует включения каждого используемого файла и snapshot в собираемый commit. Native-mode после выбора Xcode/Node до Metal/длительных тестов проверяет реальный selected Xcode27.1, iPhoneOS SDK, инструменты, формат API credentials без вывода значений, точные checkout dependencies и Swift framework imports дляarm64/iOS15. Это ограниченный SDK probe, не компиляция приложения.

Secrets listing по API недоступен403; значения credentials не читались. Наличие/формат проверяются в самом job до генерации конфигурации/ключницы/SDK. В208 те же secret references работали; API-доступ к списку не подменяет проверку runtime.

Новая версия0.9.7 согласована в workflow/реестре/заголовках. Единственная исходная аннотация перенесена0.9.6→0.9.7 с точными прежними байтами; опубликованные релизы, теги и assets не трогаются. README/LICENSE прежние. Система сборки: Telegram13.2 pin24638bc69bd083981b178dd1e7f921eebbf7fc46, Xcode27.1/Bazel9.2.0, существующее исключение tgcalls сохраняется, dependencies не обновлялись. Готовый unsigned IPA требует пользовательской подписи для установки; physical iPhone acceptance остаётся отдельной проверкой.

Проверки подготовки завершены: [receipt](RELEASE_097_PREFLIGHT_CHECKS.json). Пройдены12 команд, включая48 IPA localization regressions,7font package tests,28owner-publication contract tests,8новых input-negative tests,dependency/input-origin/member checks и workflow mode/metadata/diff. Проверены259 вызываемых скриптов и732 Python-файла,79SDKplans/73late stages. Source73 и его86 runtime-запусков не менялись; поэтому они подтверждены точным manifest, без повторного исполнения неизменённых тестов. Исторический177 также не имел concurrency; журнал раскрывает cancellation, не инициатора. Новые Apple SDK/env gates выполнятся в выбранном macOS run; здесь SDK/IPA ещё не запускались. Выбранный commit/run ID будут внесены после единственного dispatch.

210: [Actions](https://github.com/Mr-EFES/NagramiX/actions/runs/43498293300), source`1f456eca2ad36f8d4ce4a4c32bd0453ebd47a1cc`, ownerMr-EFES, clean/publishtrue, prerelease/extendedfalse. До единственного dispatch выбранногоSHA подтверждены remote main/owner/public/отсутствие активного run и дубликата. Начальные metadata/upstream/secrets/dependencies gates прошли; новый реальный iPhoneOS environment gate и MetalToolchain — success. Сейчас Apple runtime/API preflight; основная native app SDK/IPA/publication ещёpending. Поздние documentation commits не меняют выбранный source и не запускают новый run. После уточнения владельца checked retries разрешены до успешного IPA и owner publication.

210 завершился failure13ноября20:17:39UTC до применения overlay/основной SDK-компиляции. Полный build log1376строк прочитан: единственные блокирующие диагностики —2never-mutated local weak variables в generated held-edge-selection-scroll fixture. Native environment gate/все предыдущие Apple probes прошли. Исправлен только test observer в `selection_scroll_continuity_runtime.py`: weak property в отдельном probe, без сильного удержания; warnings-as-errors и все assertions прежние. 6027positivechecks×debug/O, original68 lifetime negative и2semanticnegative×debug/O проходят. [Receipt](RELEASE_097_RETRY210_CHECKS.json). Исходники приложения73, dependencies, подпись и workflow точны; Apple-повтор следующего checkedSHA ещёpending.

211: [Actions](https://github.com/Mr-EFES/NagramiX/actions/runs/43500965211),source796da9e0290cfd9185996292b43c8c9b10d6bb79, failure13ноября20:39:36UTC до overlay/SDK. Полный лог1424строк прочитан:8диагностик CGPoint.zero/CGRect accessors/CGSize integer init от одного пропущенного CoreGraphics import. Аудит всех42listed runtimefixtures и initial nullable RPC fixture выявил4использования в3модулях original-video/photo/wide. Исправлены только test imports; geometry gate до длительного набора теперь включает19границ/38запусков и прямые integer/zero/rect/offset проверки, старые Apple-only missing-import negatives сохранены. Weak-lifetime fix210 реально прошёл Apple Swift211 до перехода к70. Локальные43completefixtures/86runs,34semantic executions с ожидаемыми отказами,38geometry probes,8input tests/732syntax,metadata/diff и точный manifest73 прошли. [Receipt](RELEASE_097_RETRY211_CHECKS.json). Нативные исходники/планы/dependencies/signing/workflow не менялись; Apple повтор следующего checkedSHA ещёpending. Следующий retry разрешён последним указанием владельца.

212: [Actions](https://github.com/Mr-EFES/NagramiX/actions/runs/43504861124),source60c9cf22c2c1c566a390b9bc4584db5a783b771d. Apple early gate20:55:49–21:08:45UTC иoverlay21:08:45–22:41:27UTC13ноября прошли; cold/fake-profiles тожеsuccess. Native22:41:29–00:02:06UTC14ноября остановилась на ChatMessageItemView.swift:725 — protocolWallpaperBubbleBackgroundNode не имеетupdate. Полный журнал просмотрен: один primary Swift error; ранние210/211проблемы устранены, cancellation нет. IPA не создан.

74wide_portal_api устраняет obsolete forwarding/cache и2callers, сохраняя native portal/updateFrame ивсе остальные paths. [Контракт](WIDE_POST_PORTAL_API.md), [receipt](RELEASE_097_RETRY212_CHECKS.json). Full source74manifest91fcb7dbde584ed8ec7bb8404a36446bcf80fd34dc511957cd57f6f8b1bb33ae,37691files/26symlinks. Все4603oldinc/286oldplans и31losslesscheckpoints сохранены. Локально:478checks×2/8feature executions/16refusals,original212 typed compiler-negative,44completefixtures/88runs,650parse,74inverse/881paths,strict71×668/24headers/47597checks×2,members/native strings/mode/metadata пройдены. Первый локальныйearlylink исчерпалtmp; тот же набор прошёл сTMPDIR на более свободном workspace, production/teststrictness прежние, первоначальный лог сохранён. Verbatim protocol/native frame body заменяют неверный старый adapter; Apple native API check первым перед длинным набором иобязательная post-apply проверка добавлены. Следующий checked dispatch ещёpending; версия0.9.7, подпись/dependencies/README/LICENSE/9старых релизов прежние.


213: SUCCESS обоих заданий, run ID43535111663, source `d6a808c6af70d6ad31d678081ae73a6445c22bbf`. Единственный dispatch этого SHA; clean=true, publish_release=true, prerelease=false, extended=false, actor/triggering_actor Mr-EFES. Ранние реальные Apple SDK/API/runtime проверки прошли, включая первоначальный212 compiler-negative и fixed74 positive, полный44-fixture/88-run набор. Все74 overlay/global gates, native source checks, strict localization и cold/profile gates успешны. Полная release_arm64 компиляция01:40:44–03:28:37UTC14ноября завершилась успешно,10039 действий; затем сформированы IPA и symbols. Независимое Linux-задание повторно проверило исходный артефакт. Это настоящая компиляция приложения с SDK, не вывод из статических проверок.

Original Actions ZIP artifact14096807252 (`NagramiX-0.9.7-unsigned-arm64`, 97 559 745байт) сохранён без перепаковки, SHA256 `e0cf5b10469b50ba4049f97b05891948aa6a8690ce2bcecee3612ee0080a5765`. Symbols artifact14096737377 доступен в том же run. IPA97 996 694байта, SHA256 `50f5cb1f49d28d30c387a343e7f817e3b71a2c60b09d53c57ac87f79e8e29cc6`; version0.9.7/build213/source d6a808c, iOS15+,6ARM64/iPhoneOS binaries,71язык×668ключей настроек/debug,RU15004/668,31мелодия,8иконок,без embedded profiles. Bazel/Xcode27.1/SDK/targets/dependencies и прежняя unsigned схема не заменялись.

Owner publisher проверил оригинальный ZIP/CRC/3файла, package/provenance/SHA256, source/run/cold gate и опубликовал обычный latest v0.9.7 отMr-EFES. Все3assets загружены тем же владельцем: IPA,BUILD-PROVENANCE.txt,SHA256SUMS. Отдельный read-only verifier повторно проверил package, удалённые размеры/digests/uploader, точный tag→actual SDK source/latest/аннотацию и сохранность всех9прежних релизов,27assets,9tag targets. Receipt: RELEASE_097_PUBLICATION_CHECKS.json. Registry13pending→passed после реальной SDK/IPA проверки; всего80compile_passed,все80device_pending. Физические звук/камера/YouTube/PiP/тема/жесты не объявляются прошедшими без телефона.

Исправления задачи ограничены подготовкой0.9.7, проверками входов/Apple test boundaries и устранением несовместимого wallpaper portal API. Runtime74 удаляет устаревший абсолютный cache/forwarding и2callers в ChatMessageItemView,ChatMessageStickerItemNode,ChatMessageAnimatedStickerItemNode; все прежние стадии и контракты сохранены. Список изменённых файлов относительно подготовки main4ec205c:

- `M → .github/workflows/build-unsigned-ipa.yml`
- `M → .gitignore`
- `M → AGENTS.md`
- `M → docs/AI_HANDOFF.md`
- `M → docs/RELEASE_096_RUN.md`
- `A → docs/RELEASE_097_PREFLIGHT_CHECKS.json`
- `A → docs/RELEASE_097_RETRY210_CHECKS.json`
- `A → docs/RELEASE_097_RETRY211_CHECKS.json`
- `A → docs/RELEASE_097_RETRY212_CHECKS.json`
- `A → docs/RELEASE_097_RUN.md`
- `M → docs/RELEASE_STATUS.md`
- `M → docs/RELEASE_VERSIONING.md`
- `A → docs/WIDE_POST_PORTAL_API.md`
- `A → ios/wide_portal_api.py`
- `A → ios/wide_portal_api/After0.inc`
- `A → ios/wide_portal_api/After1.inc`
- `A → ios/wide_portal_api/After2.inc`
- `A → ios/wide_portal_api/Before0.inc`
- `A → ios/wide_portal_api/Before1.inc`
- `A → ios/wide_portal_api/Before2.inc`
- `A → ios/wide_portal_api/Guard0.inc`
- `A → ios/wide_portal_api/Guard1.inc`
- `A → ios/wide_portal_api/Guard2.inc`
- `A → ios/wide_portal_api_patches.json`
- `M → product/features/registry.json`
- `R100 → product/releases/0.9.6.md → product/releases/0.9.7.md`
- `M → scripts/feature_contract_consistency_apple.py`
- `M → scripts/feature_photo_policy_runtime.py`
- `M → scripts/feature_wide_post_envelope_runtime.py`
- `M → scripts/late_source_stages.py`
- `M → scripts/original_video_mode_runtime.py`
- `M → scripts/selection_scroll_continuity_runtime.py`
- `A → scripts/tests/test_build_inputs.py`
- `A → scripts/validate_build_inputs.py`
- `M → scripts/validate_ipa_localization_contract.py`
- `M → scripts/validate_release_095_apple_preflight.py`
- `M → scripts/validate_swift_geometry_boundaries.py`
- `A → scripts/validate_wide_portal_api.py`
- `A → scripts/wide_portal_api_runtime.py`
- `A → docs/RELEASE_097_PUBLICATION_CHECKS.json`
- `A → docs/DEVICE_CHECK_097.md`
- `M → product/features/README.md`

Заключительная запись в main меняет только документы и compile-статусы, не приложение/workflow/фактически собранный source. Команда на0.9.7 выполнена; SDK повторов больше нет,0.9.8 только по новой прямой команде. README/LICENSE/утверждённая аннотация прежние. Видимость владелец возвращает вручную через [Make private](https://github.com/Mr-EFES/NagramiX/settings#danger-zone), не автоматически.
