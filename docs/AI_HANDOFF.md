# Текущий контекст NagramiX 0.5.10

## Повтор после компиляции98

Run39043508963/build98 завершился до IPA: ASDisplayNode.gestureRecognizerShouldBegin требует override. В gesture template добавлен public override, остальные recognizers возвращаются через super вместо hardcoded true. Это точечная совместимость, не изменение сценария PiP. Исправление внесено в root и isolated source, новый retry остаётся0.5.10. Предыдущего release0.5.10 нет. Перед следующим dispatch повторить overlay и сравнить только это объявление/stock fallback; сохранить root index и прошлые releases.

## Разрешена сборка и полноценная публикация

17октября пользователь явно разрешил очередную сборку и GitHub Release с пользовательским описанием функций без технических особенностей. Новый рабочий выпуск0.5.10, попытки сохраняют эту версию. Изолированный checkout от origin/main aae9ae1d8eac41e8dc4ccf69a150b6165968f8ac: /workspace/.codex-validation-nagramix-0510/source. Root WIP и staged R100 product/releases/0.5.6.md→docs/releases/0.5.6.md сохранить. Прежние releases/tags/IPA не удалять и не заменять.

## Состав

После0.5.9/build97 добавлены только [PiP во всех направлениях](DIRECTIONAL_PIP_SWIPE.md) и [повторное исправление исключений уведомлений](NOTIFICATION_EXCEPTION_PICKER_FIX.md). Все прежние runtime-файлы совпадали с опубликованным исходником, кроме подтверждённого списка этих двух задач. Предыдущие camera/bg/cold-round/emoji/history/debug/readonly/archive/music/defaults сохранены.

PiP:4fullSHA/21exact,2GalleryUI templates; отдельный pan по подходящему central video, one finger/min zoom, controls/pinch защищены. Геометрия x/y следует свайпу, конечное системное окно размещает iOS. Галерея закрывается только после didStart или фактически active; UUID/source identity, strong один pending item, weak callbacks, bounded3s, отмена/failure возвращает видео. Native button/lazy cleanup/rotation/audio/read-state сохранить. Proof /workspace/.codex-validation-nagramix-pip-direction.

Уведомления:2fullSHA/3exact после прежнего picker helper. Временный ChatListFilter Int32.max предотвращает замену/сброс в resetFilter; empty callback не снимает header у transient bit18. Search исключает self/replies/verification из-за общего bit7 includeSelf/excludeSavedMessages; category/secret flags и store-peer перед старым editor прежние. Личные/группы/каналы/истории, archive/mute/read учитываются; новые prefs/папки не создавать. Proof /workspace/.codex-validation-nagramix-exception-recovery:595outputs,2changed/593same,3reversals/5safe rejects, grammar/Python/metadata/diff PASS.

## Проверки и выпуск

Нативная компиляция новых двух правок ещё не завершена. Реальный iPhone/Postbox/UIKit здесь не исполнялись: Linux без Xcode. Предыдущая компиляция97 не является проверкой этих изменений. Registry video_pip_swipe/notification_sounds compile_pending, device_pending. Четыре camera XCTest подготовлены ранее, не исполнены. Не обещать отсутствие всех вылетов по факту сборки.

Перед dispatch: metadata/upstream/full overlay и сравнение595outputs с последним проверенным деревом, scoped validators, Python/Swift grammar. После success: скачать новый IPA+provenance+checksums, проверить source/tag/run/version/build/CRC/6ARM64/RU+EN/31sounds/7PNG/8icons, опубликовать как полный release, записать результаты. Workflow публикует автоматически только после своих package checks; не заменять артефакт старым. Точные run/source/output фиксируются в /workspace/.codex-validation-nagramix-0510/build.json и docs/RELEASE_STATUS.md.

Следующий шаг — завершить разрешённую сборку, затем [физическая приёмка](IPHONE_TEST_0.5.10.md): все8направлений PiP для portrait/landscape/square, readiness/cancel/rotate/background/expand; все4категории исключений со списком/поиском/save/cancel/remove и cold start. Предыдущий готовый выпуск0.5.9/build97/tag3ff65e9b7d72f4d78a105df47f734df73b9e3248 сохранён; SHA25641b812d937f63a1ee5b389a90eafd98db46082d3a9c5cffbd1b541463abad1ee.
