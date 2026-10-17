# Watchdog при освобождении превью камеры

17 октября пользователь прислал crash report0.5.8/build94 и попросил устранить частые непредсказуемые закрытия приложения. Исправление исходников разрешено. Новый IPA/commit/push/release не запрошен.

## Подтверждённые данные отчёта

- iPhone18,2, iOS27.0/24A437,0.5.8/build94. Терминация: `SIGKILL`, `FRONTBOARD`, `0x8BADF00D`, `scene-update watchdog transgression`, `is stuck (deadlock)`.
- Main: `AVCaptureVideoPreviewLayer.setSession` → `AVCaptureSession._removeVideoPreviewLayer` → `_beginConfiguration` → ожидание mutex.
- `Camera.Session`: `AVCaptureSession.beginConfiguration` → `_beginConfiguration` → `sessionVideoCaptureDevices` → `objc_sync_enter` / ожидание unfair lock.
- Framework UUID `1f72a29c-6f8b-3ba4-a17e-9dea1b1986b1` совпадает с TelegramUIFramework в ранее выданном IPA94. Приложение было запущено примерно73минуты до события; этот отчёт не ограничивает проблему холодным стартом.

Этот инцидент подтверждает watchdog при взаимной блокировке capture configuration и отсоединения preview. В modern `CameraNeo` есть соответствующие конкурентные пути: session operations на `Camera.Session`, `CameraPreviewView.invalidate` с `layer.session = nil` на main, асинхронная очистка камеры при освобождении её UI. Приложение перестаёт отвечать и завершается системой. Это отдельный дефект от [передачи final-stop результата и подготовки composition](ROUND_VIDEO_COLD_FINALIZATION.md); предыдущая правка сама по себе данный lock inversion не устраняет.

Внутренние application offsets stripped binary не символицированы: dSYM не сохранялись опубликованным workflow. Нельзя приписать конкретный offset конкретной Swift-функции или утверждать, что все остальные закрытия вызваны этим же стеком. В proof сохранены только технические frames/offsets/UUID и версия, без персональных device/account identifiers из отчёта.

## Исправление владения и очередей

Все modern `CameraNeo` graphs и операции preview binding используют одну serial `nagramiXCameraSessionQueue` с прежней меткой `Camera.Session`. Это также исключает пересечение старой и новой камер при повторном использовании view. Media/GPU очереди остаются отдельными. Синхронных ожиданий на main нет.

`NagramiXCameraPreviewSession` владеет нативным `AVCaptureVideoPreviewLayer` отдельно от UIView. Binding создаётся при инициализации view до подключения session и также удерживается владельцем CameraNeo. Подключение, отключение, orientation и enabled connection changes выполняются на capture queue. UIView layout, geometry/animations, placeholder, KVO preview signal и focus-point conversion остаются в существующих UI-путях. Для синхронного `captureOrientation` используется Atomic последнего применённого orientation, без чтения connection на main.

`stopCapture(invalidate: true)` завершает native teardown и отсоединяет оба preview на той же очереди, без отложенного main callback. `CameraNeo.deinit` захватывает binding обоих слоёв вместе с session/outputs и выполняет очистку асинхронно. Native layer удерживается до detach. Camera deinit также временно удерживает обе UIView и передаёт освобождение их ownership на main после detach; main callback не вызывает session/invalidate. В escaping deinit closure нет self. Последующий recorder/processor cleanup остаётся на прежней mediaQueue.

`detach(from:)` проверяет identity ожидаемой session. Если preview уже привязан к новой камере, поздняя очистка старой камеры его не отсоединяет. При уничтожении binding без обычного invalidate fallback deinit удерживает layer/session до identity-checked detach в capture queue. Очередь и strong native-layer ownership закрывают как explicit invalidate, так и освобождение view/camera при выходе/фоне.

Shared capture queue намеренно сериализует также разные modern sessions: нельзя создавать отдельную очередь только для layer.session и оставить configuration на прежней — конкурентный захват framework locks тогда сохранится. Длительные AVFoundation операции теперь могут задержать следующую modern camera operation, но UI их не ждёт. Время повторного открытия и повороты iPad требуют физического теста.

Сохранены: public CameraProtocol/CameraSimplePreviewView API, modern/legacy selection/kill switch, доступность dual camera и ручные подключения, front/back/default rear, selfie timer/preferences, encoder/frame processor/codecs/file geometry, view-once, live-upload/export/sender, audio routing/music preference, permissions и прежние source fixes. Legacy pipeline не переписан: конкретный отчёт указывает на очередь modern CameraNeo.

## Durable overlay и проверки

- Последний `apply_camera_preview_lifecycle(source, overlay)` после cold-finalization:3full SHA inputs,21exact replacements; helper/test existence, test destination collision и все anchors проверяются до записи.
- Новая вставка `ios/Sources/CameraNeo/NagramiXPreviewSession.swift.inc` внедряется в существующий CameraPreviewView.swift. Runtime меняет только2native Swift-файла, новых production dependencies/flags/API/ресурсов нет.
- CameraNeo/BUILD дополнен только test targets. `CameraNeoPreviewTestsLib` компилирует **реальный** `Sources/CameraPreviewView.swift` вместе с тестами, без включения `-enable-testing` в production module. XCTest target: `//submodules/Camera/CameraNeo:CameraNeoPreviewTests`, runner соответствует шаблону upstream iPhone17/iOS26.5.
-4XCTest: queued invalidate при занятой capture queue; поздний detach старой session после rebind; destruction view без camera owner; удержание layer camera owner после destruction view. Только создание native session/layer, без camera permissions/inputs/Metal. Ограниченные test gates не воспроизводят сам бесконечный framework deadlock.
- `scripts/validate_camera_preview_lifecycle.py`:3SHA/21exact undo,8clean/drift/rerun/helper/test/collision сценариев без partial writes, shared owner queue, detach identity/lifetime, отсутствие main detach/sync wait и неизменность production BUILD stanza.

Proof `/workspace/.codex-validation-nagramix-camera-watchdog`: baseline593outputs =591предыдущих outputs побайтно прежние +2raw upstream inputs. Checked overlay594:3changed (2runtime+BUILD),1added XCTest,590побайтно прежних. Все предыдущие cold-finalization/emoji/edit-history/notification-picker/profile fixes сохранены. Grammar preview/helper и XCTest проходит; CameraNeo имеет один прежний parser diagnostic на `setSpecific(... value: ())`, второй исчез из-за удаления неиспользуемого per-instance sessionQueueKey. Это не Swift typecheck. Pythoncompile/metadata/diff/preservation проверяются отдельно.

**Source_checked / compile_pending / device_pending.** Apple SDK/Xcode/XCTest/AVFoundation недоступны в Linux; нативные тесты подготовлены, не выполнены. В опубликованном IPA94 исправления нет. Metadata0.5.8 прежние, новая отдельно разрешённая рабочая сборка0.5.9. Старые releases/assets и staged WIP сохраняются.

## Приёмка на iPhone

1. На устройстве/iOS из отчёта: несколько десятков open camera → record/send/cancel → close → сразу reopen, включая Избранное и обычные чаты; cold start и длительная сессия. Проверить first/repeat send и закрытие экрана без записи.
2. Foreground/background, блокировка, выход из чата, переход на другой экран при переключении и во время окончания записи; после возврата камера снова работает, старый cleanup не отключает новое preview.
3. Front/back/несколько flips/dual+single, timer OFF/ON, stop во время3–2–1, lock/record-more/trim, frame orientation и длительность/звук всех фрагментов.
4. Music ON/OFF, динамик/AirPods, permissions denied, view-once/quiet/scheduled. Legacy regression и iPad rotation/orientation отдельно.
5. Запустить новый XCTest target на доступном simulator runtime и повторить аппаратную нагрузку на iOS27. Если появится другое закрытие, сравнить новый termination/threads; один исправленный стек не подтверждает отсутствие любых будущих падений.
