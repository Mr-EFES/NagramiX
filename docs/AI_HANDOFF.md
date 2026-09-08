# NagramiX AI Handoff

## Last updated

- Date: 2026-09-01 (UTC).
- Agent: Codex, primary agent.
- Repository root used for this handoff: `/workspace/NagramiX`.

## Current project state

NagramiX is an overlay monorepo for independent Telegram clients for iOS and Android. It does not track either complete upstream tree. CI applies the iOS overlay to pinned official Telegram-iOS 12.9.2 and the Android overlay to pinned official Telegram Android 12.10.1. iOS is the product priority; all product behavior is owned and specified by NagramiX.

- Active release-preparation branch: `release/0.2.4-prerelease` (created from `origin/main` at `7a35310`).
- Functional build commit: `22ec680` (`fix: use public media aliases in copy mode`); the following documentation-only synchronization commit does not change the IPA sources.
- Tracking branch: `origin/codex/nagramix-next-fixes`; the functional build commit is pushed.
- Configured and successfully pushed origin: `https://github.com/Mr-EFES/NagramiX.git`.
- Tracked functional files were clean before adding the two handoff documents.
- Existing untracked local material: `.codex-ci-31536377921.log`, `.codex-tmp-0.1.2/`, `.codex-validation-0.1.9/`, `.codex-validation-0.2.1/` through `.codex-validation-0.2.4/`, `artifacts/` and `outputs/`. These are validation trees, logs or build artifacts, not current tracked work. Do not stage them indiscriminately.
- Latest confirmed native build: GitHub Actions run `33269968974`, successful for commit `22ec680` and version `0.2.3` build `7`.
- Latest downloaded artifact: `outputs/NagramiX-0.2.3-33269968974/NagramiX-0.2.3-unsigned.ipa`, 72,774,846 bytes, SHA-256 `2512A4EAC603FE78D7B3D1D71B2404DD160C5A3818F6A4A87FCD4EF68390FCD2`.

## Current development focus

The NagramiX settings screen has been reorganized locally into the typed categories Interface, Features and Other. Commit `6bf96de` contains that reorganization. Commit `a8cc5a3` adds the Force TCP call setting and its real one-to-one VoIP transport integration. A clean application of the combined overlay to pinned Telegram-iOS 12.9.2 passed in `.codex-validation-force-tcp-3`.

The message context-menu forward modes were corrected locally in the uncommitted `ios/apply_features.py` change. The two existing actions already passed explicit `ChatInterfaceForwardOptionsState` values, but `ChatControllerForwardMessages.swift` discarded that outer value after destination selection and used only the peer picker's `forwardOptions`. The overlay now uses `options ?? forwardOptions`: NagramiX's explicit mode wins, while ordinary Telegram forwarding with `options == nil` retains the picker's standard behavior. “Forward without author” uses Telegram's existing `ForwardOptionsMessageAttribute(hideNames: true)`, which becomes the native `messages.forwardMessages` bit 11 (`drop_author`) and suppresses local `forwardInfo`; it does not rebuild or modify `MessageObject` instances. Text entities, media/captions, custom emoji, message order and album grouping remain in the native forwarding pipeline. Secret chats, paid media and non-Premium rich messages disable the anonymous action, while the existing action-availability logic continues to block protected and self-destruct content. The distinct icon reuses Telegram's tintable `message_preview_person_off` animation.

The rear-camera video-message implementation was rewritten locally in the same uncommitted overlay. The former code manually probed only `.builtInWideAngleCamera`, disabled Telegram's dual-camera path for rear starts, replaced native pinch completion with custom neutral-zoom methods, and marked a position change immediately before recording. All four workarounds were removed. `VideoMessageCameraScreen` now snapshots the existing setting once and changes only its initial `CameraState.position`; the original `Camera.Configuration`, dual-camera decision, `CameraDevice.configure` lens selection, `Camera.togglePosition`, zoom gestures, recorder call, orientation/mirroring, flash, animations and cleanup remain intact. `CameraOutput.setInitialPosition` initializes the recorder's native stream selector without creating a switch timestamp or reopening a camera. The same device contexts and `CameraDevice.configure` path used by Telegram's switch button therefore select the initial rear camera. Missing rear-device selection falls back once to the already configured front context where possible; existing `Camera` runtime-error logging/recovery remains authoritative for later HAL/session errors. The persisted key remains `nagramix.videoMessages.useRearCamera`; only the absent-key default changed from `true` to the requested `false`, so stored user values are preserved.

The proxy settings screen now also has a completed local “Check all proxies” implementation. The action is placed after the automatic-switch timeout and before the saved-proxy list. It snapshots every unique saved proxy, leaves the enabled state, active server, DNS, calls-proxy and failover settings untouched, and refreshes Telegram's existing proxy-status context. That context still performs the real asynchronous check exclusively through the native MTProxyConnectivity API; no ICMP, socket-only probe, thread-per-proxy code or second result list was added. Generation ids reject stale callbacks after refresh or deletion. Existing stable proxy-row ids and the reactive statuses dictionary retain Telegram's standard checking, unavailable and ping presentation. The action changes to “Checking…”, ignores repeated taps, excludes deleted proxies safely, defers newly added proxies to the next batch and presents a native overlay summary. Its disposable capture is lifecycle-safe and the controller is held weakly for presentation.

Manual batch checking and automatic failover are intentionally independent. Both reuse the native MTProxyConnectivity API, but the manual screen context never updates ProxySettings; the process-wide failover controller remains the only path that may change the active proxy after its configured timeout. The existing timeout is a failover delay, not a duplicate periodic UI checker.

The user explicitly authorized the external build. Commits `05a9099` and `f6bb526` were pushed to `codex/nagramix-next-fixes`. Run `33094859022` completed the macOS/Xcode/Bazel ARM64 build, unsigned packaging, provenance recording and artifact upload successfully.

Force TCP implementation details:

- persistent key `nagramix.calls.forceTcp`, default `false`, stored by `NagramiXTabSettings` with all existing values;
- the switch and standard explanatory `ItemListTextItem` are in Features / Calls;
- `TelegramVoip.OngoingCallContext` snapshots the setting once while creating a new one-to-one call context, covering incoming/outgoing and audio/video calls;
- when enabled, it adds Telegram/tgcalls custom parameter `network_use_tcponly`, retains only connection descriptions whose existing `hasTcp` flag is true, disables P2P and passes `allowTCP: true`;
- when disabled, the original endpoint list, P2P value, custom parameters and `enableTCP` behavior are unchanged;
- the integration is scoped to `TelegramVoip`; MTProto, messages, downloads and proxy settings are untouched.

Force TCP local verification: Python compilation, repository and generated-tree `diff --check`, clean pinned-overlay application, UI/persistence/source-scope inspection passed. Native macOS compilation and physical-device incoming/outgoing audio/video call tests remain pending until external build authorization and device testing.

Implemented locally:

- typed `NagramiXSettingsCategory` with `.interface`, `.features` and `.other`;
- all 14 existing settings retained and filtered through the explicit category property;
- a localized Proxy Settings disclosure that opens Telegram's existing `proxySettingsController(context:)` through the current navigation controller;
- a NagramiX-specific equal-width segmented-title mode with bold labels and full-width selection sections;
- Russian and English resource strings for Interface, Features, Other and Proxy Settings.

Static verification passed: Python compilation, `git diff --check`, clean pinned-overlay application, required localization presence and the presence of all 14 previous settings. Native compilation and physical-device UI/runtime verification remain pending.

## Recently completed

The following is supported by commit `21802bf`, the tracked sources and current project documentation:

- Prepared test version 0.2.1 and updated the unsigned build workflow to emit `NagramiX-0.2.1-unsigned.ipa`.
- Added the NagramiX information block: Features, Updates and Help, with puzzle/megaphone/message icons and the project website, update channel and help bot destinations.
- Inverted and migrated the proxy sponsor setting to `hideProxySponsorChannel`, defaulting to hidden.
- Hardened proxy failover state against competing timers and stale asynchronous callbacks.
- Continued fixes for story-view confirmation, rear-camera video messages and zoom behavior through exact upstream patches in `ios/apply_features.py`.
- Kept the clean-install defaults for Russian localization, dark theme and the built-in game wallpaper, without intentionally overwriting established user choices.
- The previous 0.1.9/0.2.0 work introduced the DNS selector and DoH resolver path, custom DoH validation, proxy auto-switch controller, persistent proxy button, tab controls, story controls, eight application icons and Russian Debug-menu localization.

These statements describe implemented code and build history. They do not imply that every runtime scenario has been verified on the latest physical-device build.

## Completed in the 0.2.2 build

The earlier forwarding, round-video and proxy work plus the deleted-message/edit-history implementation are committed and included in the successful 0.2.2 native build. The durable feature sources are under `ios/`, not in a generated validation tree:

- `ios/Sources/TelegramCore/NagramiXMessageArchive.swift` — new account-owned, asynchronous local snapshot archive. It stores only received incoming cloud messages, text/caption entities, safe image/file references and peer data; it excludes secret chats, verification-code chats, copy-protected peers/messages, autoremove/autoclear/view-once/ephemeral content and paid media.
- `ios/Sources/NagramiXCore/Sources/NagramiXTabSettings.swift` — persists `nagramix.messages.showDeletedMessages` and `nagramix.messages.editHistory`, both defaulting to `false`.
- `ios/Sources/SettingsUI/NagramiXSettingsController.swift` — adds the FEATURES / MESSAGES switches, explanatory rows and confirmed local-archive cleanup action.
- `ios/Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift` and `Resources/{en,ru}.lproj/Localizable.strings` — add all message-archive labels and actions without Swift string literals.
- `ios/apply_features.py` — copies the archive into TelegramCore and uniquely anchors integration into Account, state mutation, interactive deletion, chat-history rendering, bubble status and the message context menu. It also restores a missing CLI entry point so `python ios/apply_features.py --telegram-dir ...` actually applies the overlay.
- `ios/Sources/SettingsUI/ProxyListNagramiXBlock.swift.inc` — contains the committed proxy batch-check work.

The archive is keyed by peer/message namespace/message id and stored as `nagramix-message-archive.json` inside the account `basePath`. Telegram's existing `managedCleanupAccounts` removes the complete `account-*` directory after logout/removal, so the archive follows account data cleanup. Synthetic deleted messages are built only for the active `MessageHistoryView` conversion and are never inserted into Postbox; they therefore do not participate in unread counts, notifications, chat-list ordering/last-message, search, read state or server actions. Context actions on synthetic messages are restricted to Copy, Edit History and local Delete.

Local validation passed: Python compilation, repository `git diff --check`, duplicate/missing localization checks, clean full overlay application to Telegram-iOS SHA `6ad963e5b62d354da79040f388ae2b9132fb17b8`, unique new anchors and generated-tree `git diff --check`. Native macOS/Xcode/Bazel compilation then passed in run `33094859022`. Physical-iPhone runtime and crash regression tests remain pending and must not be inferred from compile success.

The pre-existing `README.md` modification is unrelated and must not be folded into these feature changes without separate review. `AGENTS.md`, `docs/AI_HANDOFF.md`, validation checkouts, logs and artifacts remain untracked; the new archive source is also currently untracked in the dirty worktree and must be included when the intended overlay change is eventually committed. Validation copies are not authoritative feature sources.

## Important architecture/context

1. **Overlay, not full fork.** `ios/apply_overlay.py` is the CI entry point. It generates a temporary configuration from environment secrets, changes pinned branding/build anchors, creates app-icon assets and invokes `apply_features(source)`.
2. **Pinned upstreams.** `ios/upstream.env` pins Telegram-iOS commit `6ad963e5b62d354da79040f388ae2b9132fb17b8`; `android/upstream.env` pins official Telegram Android 12.10.1 at commit `b7561f0c641b521df0000bda2704664d792d6a1a`.
3. **Fail-fast patching.** `ios/apply_features.py` uses exact single-occurrence anchors and ranges. A missing anchor aborts the overlay instead of silently producing a partially branded or partially functional build. Updating Telegram-iOS requires auditing these patches.
4. **Isolated custom code.** Custom Swift/Objective-C sources live under `ios/Sources/` and are copied into the temporary Telegram tree. Bazel dependencies and small upstream integrations are then added by the patcher.
5. **Settings persistence.** `NagramiXTabSettings` stores tab, camera, story, DNS, proxy and interface choices in `UserDefaults`, publishes change notifications and contains the sponsor-setting migration. Persisted-key compatibility matters.
6. **DNS integration.** `NagramiXDNSResolver` is copied into MtProtoKit and patched into the `MTDNS` resolution path. The selected provider is represented by one typed `NagramiXDnsProvider`. Inspect the actual MtProtoKit call path before expanding claims about which traffic is resolved through DoH.
7. **Proxy failover.** `NagramiXProxyFailoverController` lives in TelegramCore, observes connection/proxy state, delays according to 15/30/60-second settings, checks candidates through existing Telegram proxy-connectivity infrastructure, updates real `ProxySettings` and invalidates stale work. It must remain independent of the proxy settings screen lifecycle.
8. **UI patches.** Tab layout, settings placement, proxy button, stories, camera/video-message behavior, Debug localization, information rows and icons are integrated into pinned TelegramUI/SettingsUI/Camera paths by `apply_features.py`.
9. **Unsigned build.** CI uses generated self-signed build-only profiles to satisfy the native build, then `scripts/package_unsigned_ipa.sh` removes signatures and provisioning profiles before producing the distributable IPA. No Apple signing secrets are required or stored.
10. **Extensions.** The current build disables Telegram extensions. Do not assume extension targets share the app's new bundle IDs or entitlements.

## Important files

- `.github/workflows/build-unsigned-ipa.yml` — full macOS runner pipeline, version, pinned checkout, Bazel build and artifact upload.
- `README.md` — project identity, current version, feature summary and build outcome.
- `docs/BOOTSTRAP.md` — bootstrap/build model and risk map; some wording still reflects the 0.2.0 iteration.
- `docs/NAGRAMIX-0.1.7.md` through `docs/NAGRAMIX-0.2.0.md` — historical test-version notes and physical-device checklists.
- `ios/upstream.env` — authoritative pinned Telegram-iOS SHA/version.
- `ios/configuration.template.json` — non-secret build configuration template and NagramiX bundle metadata.
- `ios/apply_overlay.py` — branding/configuration/icon orchestration and feature-overlay entry point.
- `ios/apply_features.py` — all exact upstream integration patches; highest-risk maintenance file.
- `ios/generate_fake_profiles.py` — temporary self-signed profile generation on macOS.
- `scripts/package_unsigned_ipa.sh` — unsigned IPA packaging and final metadata checks.
- `ios/Sources/NagramiXCore/Sources/NagramiXTabSettings.swift` — typed DNS provider, persistent feature settings, defaults, migration and notifications.
- `ios/Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift` — NagramiX localization accessors layered on Telegram presentation data.
- `ios/Sources/NagramiXCore/Resources/{en,ru}.lproj/Localizable.strings` — English and Russian NagramiX strings.
- `ios/Sources/SettingsUI/NagramiXSettingsController.swift` — main NagramiX settings UI.
- `ios/Sources/SettingsUI/NagramiXCustomDohController.swift` — HTTPS DoH URL validation/edit UI.
- `ios/Sources/SettingsUI/ProxyListNagramiXBlock.swift.inc` — replacement proxy screen block injected into pinned SettingsUI.
- `ios/Sources/TelegramCore/NagramiXProxyFailoverController.swift` — runtime proxy failure monitor and failover coordinator.
- `ios/Sources/TelegramCore/NagramiXMessageArchive.swift` — account-scoped local deleted-message and edit-revision snapshot service.
- `ios/Sources/MtProtoKit/NagramiXDNSResolver.{h,m}` — DNS-over-HTTPS implementation for MtProtoKit integration.
- `ios/branding/AppIcons/1.png` through `8.png` — authoritative app-icon source images.

## Decisions already made

- Keep NagramiX custom behavior isolated from upstream whenever practical so Telegram-iOS updates remain reviewable.
- Maintain a separate bundle identifier: `com.mr-efes.nagramix`.
- Produce unsigned ARM64 IPA files without Apple certificates or signing secrets in the repository.
- Keep Telegram-iOS pinned until a deliberate upstream migration audits all exact patch anchors.
- Keep the Android and iOS applications independently compiled and platform-native; parity is user-visible behavior, not shared platform code.
- Keep eight NagramiX icons only; icon 1 is the real primary icon and icons 2–8 are alternates.
- Default tab behavior: Contacts and Calls hidden, titles shown, separate Search button hidden.
- Default video-message camera preference: front camera; enabling the existing setting changes only the next round-video recorder's initial position to rear.
- Default DNS provider: system. Default proxy auto-switch: off with 15-second stored interval. Default persistent proxy button: on.
- Default proxy sponsor channel behavior: hidden, with migration from the former opposite-semantic key.
- Keep UI strings in NagramiX localization resources instead of hardcoding user-visible Russian strings.
- Use existing Telegram navigation, networking, theming and proxy mechanisms instead of parallel frameworks.

## Known issues

- NagramiX 0.2.1 compiled successfully, but full 0.2.1 physical-iPhone regression results have not yet been recorded. Do not convert compile success into a claim that every story, camera, zoom, DNS or failover scenario is proven.
- The latest IPA is unsigned and must be signed externally before installation.
- Native iOS compilation cannot be performed in the current Windows workspace; use the macOS GitHub Actions pipeline.
- `ios/apply_features.py` is large and tightly coupled to the pinned upstream text. It is intentionally fragile across upstream revisions.
- No dedicated automated unit-test or lint target for the overlay repository was discovered during this audit.
- The message archive can only retain content and revisions actually received by this client after a feature is enabled. Telegram exposes no API for recovering earlier deletions or unseen edits.
- The current archive persists compact snapshot metadata in one account-local JSON file. UI conversion is range-filtered and limited to 200 deleted entries per history update, but a future large-scale iteration should move storage to a sharded/Postbox-backed index before claiming stress validation for very large archives.
- Image/file media is stored as Telegram resource metadata only. It is not downloaded for the archive; deleted media whose resource is absent from local cache may show the native unavailable placeholder while its caption remains available.
- Empty-caption media does not yet get a separate media-node Deleted badge; the implemented bubble marker covers text and supported media captions. Native build/device testing must decide whether a dedicated media overlay is needed.
- Temporary validation trees and downloaded artifacts are untracked and can create noisy `git status` output. Do not treat them as authoritative sources or stage them accidentally.
- `docs/BOOTSTRAP.md` and part of `README.md` retain wording centered on 0.2.0 even though the current workflow version is 0.2.1. This is a documentation consistency issue, not an instruction to modify it during unrelated tasks.
- The configured Git remote is `https://github.com/Mr-EFES/NagramiX.git` for fetch and push.

## Build / Test

### Full native build

The confirmed and authoritative build is `.github/workflows/build-unsigned-ipa.yml` on `macos-26`.

Required repository secrets:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

The workflow performs these verified stages:

1. Read `ios/upstream.env`.
2. Check out Telegram-iOS with recursive submodules at the pinned SHA.
3. Verify `versions.json` reports Telegram `12.9.2` and select its required Xcode.
4. Run:

   ```bash
   python3 ios/apply_overlay.py \
     --source Telegram-iOS \
     --configuration "$RUNNER_TEMP/nagramix-configuration.json"
   ```

5. Generate temporary build-only profiles with `ios/generate_fake_profiles.py`.
6. Build Telegram-iOS with its native `build-system/Make/Make.py`, configuration `release_arm64`, through Bazel.
7. Package and validate the unsigned app with `scripts/package_unsigned_ipa.sh`.
8. Upload `NagramiX-0.2.3-unsigned.ipa` and `BUILD-PROVENANCE.txt` as an Actions artifact.

The workflow can be started with GitHub Actions `workflow_dispatch` or by a pull request change under its configured paths.

### Safe local static checks

From the repository root, Windows/macOS/Linux agents can run:

```text
python -m py_compile ios/apply_overlay.py ios/apply_features.py ios/generate_fake_profiles.py
git diff --check
```

JSON/XML/SVG resources changed by a task should also be parsed or validated with available standard tools.

Applying the full overlay requires a clean checkout of the exact pinned Telegram-iOS revision and valid temporary environment values for `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`. Prefer the CI workflow as the reproducible implementation of that process.

### Installation/manual testing

The produced IPA is unsigned. Sign it externally, install it on a physical iPhone, and use the relevant release checklist in `docs/`. Clean-install defaults and iOS icon cache behavior require removing the previous application before testing.

## Validation status

- Compile: **PASS** — GitHub Actions run `33094859022` completed successfully for commit `f6bb526` and produced the 0.2.2 artifact.
- Overlay application/static integration before that build: **PASS** as part of the successful CI pipeline.
- Automated unit tests: **NOT RUN / no overlay-specific suite discovered**.
- Lint: **NOT RUN / no overlay-specific lint job discovered**.
- IPA archive integrity: **PASS** — ZIP validation passed; the artifact contains `Payload/NagramiX.app/Info.plist` and the ARM64 Mach-O `Payload/NagramiX.app/Telegram`, bundle id `com.mr-efes.nagramix`, version `0.2.3`, and no `_CodeSignature` or `embedded.mobileprovision`; SHA-256 recorded above.
- Manual verification of 0.2.1 on a physical iPhone: **PENDING / not recorded in the repository**.
- Latest deleted-message/edit-history overlay: **STATIC PASS / NATIVE PASS / DEVICE PENDING** — clean pinned application, unique new anchors, Python compilation, localization checks, overlay/generated `git diff --check` and macOS ARM64 compilation passed; physical-device behavior is not yet verified.

## Next recommended steps

1. Read `AGENTS.md` and this file.
2. Run `git status` and isolate the intended tracked overlay files from existing local artifacts and the unrelated README modification.
3. Do not start a feature without a concrete user request.
4. When the next feature or bug report arrives, inspect the relevant overlay source and the exact pinned upstream integration points before editing.
5. For claims about 0.2.1 runtime behavior, obtain and record physical-iPhone test results.
6. Review and commit only the intended tracked overlay files listed under **Work in progress**; do not stage validation trees, logs, unrelated README work or artifacts.
7. After a fresh explicit authorization to send code externally, push the intended local commits and trigger/monitor the macOS unsigned-IPA workflow. Then test forwarding modes and the full physical-device round-video matrix: setting off/on, repeated opens, cancel, switch in both directions, zoom before/after switch, rotation, background/foreground, permissions and camera-unavailable recovery.

## Files modified in the latest session

- `ios/Sources/TelegramCore/NagramiXMessageArchive.swift` — new persistent account-local snapshot service and synthetic deleted-message model.
- `ios/Sources/NagramiXCore/Sources/NagramiXTabSettings.swift` — adds the two default-off persisted message switches while retaining earlier settings work.
- `ios/Sources/SettingsUI/NagramiXSettingsController.swift` — adds the FEATURES / MESSAGES controls and confirmed archive cleanup.
- `ios/Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift` and `Resources/{en,ru}.lproj/Localizable.strings` — add message-archive UI strings while retaining prior proxy strings.
- `ios/apply_features.py` — integrates capture-before-edit/delete, local-delete suppression, synthetic history entries, Deleted bubble status and formatted Edit History context action; it also restores the executable CLI footer and enforces unique anchors for the new integration.
- `docs/AI_HANDOFF.md` — records the archive architecture, static validation, exclusions and remaining native/device limitations.

No workflow, build configuration or new image asset was intentionally changed during this session. Generated Telegram sources were changed only inside disposable validation worktrees; the durable implementation remains in the tracked overlay.

## Handoff notes

- Work only in the Git root `D:\NagramiX\IA\referenced-chatgpt-conversation-this-is-an`; do not resume work from the former `C:` workspace copy.
- Do not edit `.codex-validation-*`, `work/Telegram-iOS-*` or another downloaded checkout as the durable solution. Change the tracked overlay and verify that it applies to a clean pinned upstream tree.
- Keep secrets out of patches, logs and handoff documents.
- Before closing the next session, replace stale state in this file with verified current facts rather than endlessly appending chat history.

## Built 0.2.3 iPhone test version

### Offline/proxy startup and Copy as New hardening (2026-08-29)

The tracked overlay includes the two additional fixes built into the 0.2.3 test version.

Offline/proxy changes:

- `NagramiXProxyFailoverController` remains entirely on its dedicated `SwiftSignalKit.Queue`; account/UI construction never waits for a proxy check.
- `.waitingForNetwork` is treated as a normal state. It cancels pending timers/probes and does not classify the active proxy as broken.
- the `MTProxyConnectivity` error channel is handled explicitly. A DNS/socket failure advances to the next candidate instead of escaping or leaving the state machine stuck;
- if connectivity disappears after automatic failover temporarily selected a candidate, the controller restores the original user-selected proxy only when the current value still matches the controller's own candidate. A concurrent manual proxy change is not overwritten;
- failed DoH requests use non-nil local errors, `NSURLSessionConfiguration.waitsForConnectivity = false`, generic non-sensitive logging and the existing `MTTcpConnection` close/reconnect path. No hostname, proxy address, credentials, password or MTProto secret is logged;
- Telegram's proxy list checker maps its checker's error channel to the existing `.notAvailable` state. No ICMP/socket-only checker or main-thread network operation was added.

No `.ips`, `.crash`, device console or symbolicated stack trace was present in the project, and the Windows host cannot reproduce Airplane Mode on an iPhone. Therefore the exact original runtime stack trace is still unavailable. The verified source-level risk was the NagramiX-added DNS/failover error path around account networking, not Telegram's local UI/database bootstrap. A physical-device crash log is still required if the issue reproduces after the new build.

Copy-as-new changes:

- `NagramiXMessageTransferMode.copyAsNew` is distinct from `.forwardWithSource` all the way through destination selection;
- copy mode no longer gives the picker `forwardedMessageIds`, so forward-only options do not leak into this operation;
- classic forwarding still builds `.forward` values with native `ForwardOptionsMessageAttribute` behavior;
- copy mode builds only new `EnqueueMessage.message` values. It copies text/caption entities, custom-emoji associated media, supported image/file/contact/map references, spoiler state and fresh per-operation album grouping keys;
- copy mode sets no `ForwardOptionsMessageAttribute`, reply id or story reply id and never mutates the source `Message`;
- protected, secret-media/self-destruct, expired and paid content is rejected before copy mode is offered;
- TelegramCore's normal enqueue path creates the result with `forwardInfo: nil` and derives the author from the current account or native channel/send-as rules. Text and supported captions are therefore editable through Telegram's ordinary edit rules; media types that Telegram normally does not allow editing remain non-editable.

Validation for these latest fixes:

- Python compilation of `apply_overlay.py`, `apply_features.py` and `generate_fake_profiles.py`: PASS;
- repository `git diff --check`: PASS;
- clean overlay application to Telegram-iOS `6ad963e5b62d354da79040f388ae2b9132fb17b8`: PASS;
- all exact anchors used by the overlay: PASS;
- generated-tree `git diff --check`: PASS;
- static invariants for asynchronous failover, DNS error handling, `.copyAsNew`/`.forward` separation, `forwardInfo: nil`, current-account/native-send-as authorship, entities, custom emoji, media, grouping and protected-content rejection: PASS;
- localization duplicate check and English-to-Russian fallback coverage: PASS;
- native Xcode/Bazel build for these latest changes: PASS in workflow `33269968974`;
- Airplane Mode/proxy recovery and copy/edit tests on a physical iPhone: PENDING.

Authoritative changed files for this fix are `ios/Sources/TelegramCore/NagramiXProxyFailoverController.swift`, `ios/Sources/MtProtoKit/NagramiXDNSResolver.m`, `ios/apply_features.py` and this handoff. The clean generated validation tree is `.codex-validation-offline-copy4-0.2.3` and must not be committed.

The tracked overlay contains the six user-requested follow-up fixes included in build 0.2.3:

- clean-install appearance uses Telegram's built-in dark-blue `.nightAccent` theme and its native wallpaper; saved appearance settings are untouched;
- the Profiles settings retain Profile ID and approximate registration date, remove the chat-creation-date feature, make the displayed numeric ID copyable with Telegram's `UndoOverlayController`, and add the default-off mutual-contact badge preference;
- `ContactsPeerItem` reads Telegram's real `UserInfoFlags.mutualContact` and appends a theme-tinted people icon only for non-self, non-bot, non-deleted mutual users;
- the three settings categories keep equal one-third tab layout while the title view uses low horizontal hugging/compression priorities and adaptive intrinsic sizing to occupy the navigation width left after Back;
- “Forward with source” uses the untouched Telegram forward flow, while “Forward without source” uses the typed `.copyAsNew` path and creates new `EnqueueMessage.message` values with text entities, supported media references, spoilers and fresh album grouping keys, but without forward/reply metadata;
- story confirmation is a full-screen pre-view controller backed by the selected story's native cached thumbnail signal; it does not open or mark the story seen until confirmation and does not auto-fetch the full media.

Prepared build metadata:

- version: `0.2.3`;
- application bundle id: `com.mr-efes.nagramix`;
- localization bundle id: `com.mr-efes.nagramix.localization`.

Local validation on 2026-08-29:

- Python compilation of all overlay scripts: PASS;
- overlay application to Telegram-iOS SHA `6ad963e5b62d354da79040f388ae2b9132fb17b8`: PASS;
- exact-anchor enforcement: PASS;
- overlay and generated-tree `git diff --check`: PASS;
- localization duplicate check: PASS; every English NagramiX key has a Russian counterpart;
- native macOS/Bazel compilation: PASS in workflow `33269968974`;
- physical-iPhone behavior and crash testing: PENDING.

The disposable validation worktree is `.codex-validation-ready-0.2.3`; it is not a durable source and must not be committed. Stage only the tracked overlay/build metadata and this handoff file, never the validation trees, artifacts, logs or the unrelated existing README edit.

## NagramiX 0.2.3 native test build (2026-08-29)

- Successful workflow: `33269968974`, job `99146579963`, commit `22ec68018c160fd57e5b1f2959050ce87bc9bcf1`.
- Native macOS/Xcode/Bazel release ARM64 compilation: **PASS**.
- Overlay application, unsigned packaging, provenance recording and artifact upload: **PASS**.
- Artifact: `NagramiX-0.2.3-unsigned-arm64` (GitHub artifact id `9720430103`).
- Downloaded IPA: `outputs/NagramiX-0.2.3-33269968974/NagramiX-0.2.3-unsigned.ipa`.
- IPA ZIP validation: **PASS**; `Payload/NagramiX.app/Info.plist` is present.
- Metadata: bundle id `com.mr-efes.nagramix`, short version `0.2.3`, build `7`, ARM64 Mach-O CPU type `0x0100000c`.
- IPA SHA-256: `2512A4EAC603FE78D7B3D1D71B2404DD160C5A3818F6A4A87FCD4EF68390FCD2`.
- The IPA intentionally has no `_CodeSignature` and no `embedded.mobileprovision`; external signing is required before installation.
- The first build attempt exposed a missing mandatory `completed` callback in the Swift bridge for `MTSignal.start`; commit `146c158` fixed it.
- The second build exposed unavailable direct Postbox type names in TelegramUI copy mode; commit `22ec680` switched to public `EngineMedia.Id` / `EngineRawMedia` aliases.
- Physical-iPhone runtime, offline/proxy recovery and copy-as-new/editability verification: **PENDING USER TEST**. Native compilation alone does not prove these runtime scenarios.

## NagramiX 0.2.4 pre-release preparation (2026-09-01)

The 0.2.4 pre-release changes release metadata and documentation before the native build:

- `.github/workflows/build-unsigned-ipa.yml` now packages `NagramiX-0.2.4-unsigned.ipa`;
- `README.md` identifies 0.2.4 as a pre-release;
- `docs/NAGRAMIX-0.2.4.md` records the current feature set, verified scope, known limitations and the physical-device test matrix;
- `.github/workflows/publish-prerelease.yml` transfers a successful Actions artifact directly into an existing GitHub pre-release; this avoids relying on a local host's access to the Azure Actions-artifact CDN;
- no product source or pinned Telegram-iOS revision was changed for this version bump.

Native macOS/Xcode/Bazel run `33513250714` succeeded for commit `3fb56f6abb0c1001472d06d68f235eaea68b25bb`; its packaging, provenance and artifact-upload steps passed and produced Actions artifact `NagramiX-0.2.4-unsigned-arm64` (artifact id `9805797797`, 72,514,272 bytes). Local download was not possible because this environment's CONNECT proxy returned HTTP 403 for the Azure Actions-artifact CDN, so local plist/Mach-O/SHA-256 inspection was not claimed. The publisher workflow validates the artifact ZIP before attaching the IPA and provenance to GitHub. Static verification completed: Python compilation for all three overlay scripts, YAML parsing, `git diff --check`, shell syntax for the IPA packager, JSON parsing for the configuration template, and localization coverage/duplicate checks. Physical-device testing remains pending after publication.

## Android monorepo baseline (2026-09-01)

This historical Android baseline is superseded. The current Android overlay uses only the pinned official Telegram Android source and NagramiX-owned Kotlin/Java integrations.

`.github/workflows/build-android-apk.yml` checks out the pinned Android source recursively, applies the overlay, uses the existing Telegram API repository secrets, installs JDK/SDK/NDK tooling, builds an ARM64 debug APK, validates package/version/signature metadata, records SHA-256/provenance and uploads the test artifact. The generated debug signing key is not a stable production identity; users may need to uninstall a differently signed earlier build.

`docs/ANDROID-FUNCTION-PARITY.md` is the durable parity matrix. Source-level availability or a successful Gradle build must not be presented as physical-device verification. Current verification: overlay application to a clean pinned checkout, exact anchors, Python compilation, YAML parsing and overlay/generated-tree `git diff --check` pass. Native Gradle/NDK CI and all physical-device rows remain pending. Exact next step: push the branch, let the Android workflow build the APK, inspect its metadata/signature/SHA-256, then install it on an ARM64 Android device and record every matrix result or mismatch.

The first historical Android CI attempt, run `33543465270`, failed during SDK installation before compilation. No APK was produced by that attempt.

### Android 0.2.4 native CI result

Android run `33543742039` succeeded for commit `55211affebbb12a430d07772d340e61f73b082b5`. Gradle completed in 29m10s and produced artifact `NagramiX-0.2.4-android-arm64` (artifact id `9815786610`, archive size 67,568,542 bytes). Validated APK metadata: package `com.mr_efes.nagramix`, version code `204`, build version `0.2.4-f828a0c`, compile SDK 37. `apksigner` verified APK Signature Scheme v2 with the ephemeral Android Debug certificate; certificate SHA-256 is `f35b50bf9de6e1fb3780eaa945d10e57343c685cf605973f67d57245c5c4a7b3`. APK SHA-256 is `b6347954016ba9e5d37ca34e6a80d793d0dafa3b52e91b7bc847c92066639937`. Compilation and packaging are proven; physical-device functionality remains pending.

`.github/workflows/publish-android-prerelease.yml` transfers the validated Actions artifact to an existing GitHub pre-release without exposing credentials or depending on a local artifact CDN download. After merge, dispatch it for run `33543742039`, artifact `NagramiX-0.2.4-android-arm64`, tag `v0.2.4-rc1`. The exact next step after publication is to install the APK on an ARM64 Android device and record results in `docs/ANDROID-FUNCTION-PARITY.md`.

The first Android publisher run `33547055308` verified the complete APK ZIP but failed its checksum command because the checksum file stores a basename while the workflow ran from the repository root. The validation was corrected to execute `sha256sum --check` inside `release-assets`; the downloaded APK itself was not implicated.

Android publisher run `33547148058` then passed ZIP integrity, SHA-256 verification and release upload. GitHub pre-release `v0.2.4-rc1` now contains `NagramiX-0.2.4-android-arm64.apk` (77,171,492 bytes, SHA-256 `b6347954016ba9e5d37ca34e6a80d793d0dafa3b52e91b7bc847c92066639937`) alongside the iOS IPA and Android metadata, signature, checksum and provenance files. PRs `#4` and `#5` are merged. Remaining work is exclusively physical-device Android testing and any fixes it reveals; record results in `docs/ANDROID-FUNCTION-PARITY.md` without upgrading Pending rows based on compilation alone.

## Android architecture correction: official Telegram base (2026-09-01)

The product owner clarified the authoritative architecture: NagramiX is an independent application; iOS is the priority platform, Android is a first-class secondary platform, and both start from official Telegram repositories. iOS features are implemented natively in Swift/Objective-C and Android counterparts in NagramiX-owned Kotlin/Java.

The earlier Android artifact and parity claims are superseded and must not be treated as the current independent Android client. The replacement pin is official `DrKLO/Telegram` commit `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, whose `gradle.properties` reports 12.10.1 (7038). `android/apply_overlay.py` was rewritten for this official tree: it sets independent version/package metadata, injects NagramiX branding and a Kotlin-owned settings namespace, uses repository-secret Telegram API credentials through generated BuildConfig fields, disables official-only update/passkey behavior, configures independent debug signing and limits the development APK to ARM64.

The parity matrix was reset to honest implementation states. Most product features are **Not ported** on the corrected official Android base; successful compilation cannot change those states. The prior APK must be removed/replaced in `v0.2.4-rc1` after the corrected official-base CI succeeds. Exact next step: apply the rewritten overlay to a clean official checkout, run static checks, build in Android CI, verify package/signature/provenance, replace the pre-release APK, then implement matrix rows one by one with Kotlin/Java and Samsung device tests.

## Repository product/systematization pass (2026-09-01)

The owner approved a three-layer monorepo: `product/` defines NagramiX behavior and settings, `ios/` implements it against official Telegram-iOS, and `android/` implements it with NagramiX-owned Kotlin/Java against official Telegram Android. iOS remains the implementation priority; Android parity is a required follow-up rather than a claim inferred from another client.

Changes in this pass:

- moved the former iOS-specific `nagramix/` tree to `ios/` and updated authoritative workflows/documentation without changing persisted `nagramix.*` setting keys;
- added platform-neutral product identity, settings contract, terminology, compatibility, feature registry, feature lifecycle, upstream policy and 0.2.4 scope under `product/`;
- added `scripts/check_upstreams.py` plus scheduled/manual CI audit, and made IPA/APK builds require current official pins;
- verified official master on 2026-09-01: Telegram-iOS is 12.9.2 at `6ad963e5b62d354da79040f388ae2b9132fb17b8`; Telegram Android is 12.10.1 (7038) at `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`;
- migrated the corrected Android overlay to that current official Android commit and SDK 36;
- documented current minimums from official sources: iOS 13.0 and Android API 21 / Android 5.0;
- rewrote README around the independent, unofficial, non-commercial product, official bases, directory layout, compatibility, pre-release model and honest Android backlog.

Static verification completed: official upstream audit with `--require-current`, Android overlay application to a clean official checkout, Python compilation, JSON parsing, workflow YAML parsing, embedded shell syntax and repository/generated-tree `git diff --check`. Native IPA was not rebuilt because iOS product code did not change. The restructured current-official Android APK requires a fresh GitHub Actions build before the obsolete non-current-base APK release asset can be replaced. Physical-device validation remains pending.

Exact next step: authenticate GitHub CLI, synchronize with `origin/main`, push this focused restructuring commit, create a PR, run Android CI, inspect APK metadata/signature/provenance, replace the old Android release asset only after success, then continue feature ports from `product/features/registry.json` in iOS-priority order.

## PR #7 review follow-up (2026-09-02 UTC)

Addressed every inline review item: Android now uses canonical `interface.hideStories`; the shared outgoing-call confirmation default matches the shipped iOS `true`; Android documentation names official Telegram 12.10.1; icon status remains `not_started` until compilation; scheduled upstream checks fail when pins become stale; and the launcher source is owned by `android/branding`. The Android overlay also removes the Google Services plugin from the repackaged application, fixing CI's `processAfatDebugGoogleServices` failure for the independent package id.

Changed files are the six reviewed files, `android/branding/AppIcons/1.png`, `android/apply_overlay.py`, and this handoff. Static validation passed before commit. Native Android CI is rerunning; physical Android and iPhone testing remains pending. Exact next step after a green Android build is to keep implementing the product registry rather than publish a parity APK.

Sparse clean-pin overlay validation initially found a trailing blank line after plugin removal. The exact anchor was widened to consume the separator plus plugin line; the rerun applied successfully and generated-tree `git diff --check` passed.

## Android wide channel posts and source audit (2026-09-08 UTC)

GitHub CLI authorization was restored for `Mr-EFES` without placing a token in
the repository remote. The Android parity history was recovered from
`origin/feature/android-0.2.4-parity-next`, synchronized with current `main`,
and continued on `work/feature/android-0.2.4-source-parity`.

Android now has the native counterpart of `interface.wideChannelPosts`, default
off. The setting is exposed under Interface. For an ordinary main-timeline post
whose peer is a broadcast channel, `ChatMessageCell` suppresses its floating
share/summarize controls and adds their 40 dp side allowance to native message
measurement. Replies, threads, pinned/search/custom preview presentations,
sponsored messages and megagroups retain official layout behavior. Text,
media, reactions, comments and context actions remain in Telegram's existing
cell pipeline.

The overlay applied cleanly to official Telegram Android 12.10.1 at
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`; Python compilation and both
repository and generated-tree `git diff --check` passed. Native Gradle/NDK
compilation and physical-device layout testing remain pending.

The final source audit is recorded in `docs/ANDROID-SOURCE-AUDIT.md`. Full
source parity is not yet achieved: deleted/edit archives require final review,
proxy failover is not ported, and offline-startup behavior is unaudited. APK
workflows must remain disabled. Exact next step: close those three source
blockers, pass `scripts/check_android_release_ready.py --release 0.2.5`, then
restore the ARM64 APK workflow and run native CI.

PR #9 inline review findings were addressed on 2026-09-08: the System DNS
choice now calls Android's `InetAddress` resolver rather than Telegram's remote
HTTP resolver; custom DoH validation uses a fragment-owned executor and rejects
callbacks after dialog dismissal/provider changes or fragment destruction;
group/channel profile IDs use the same positive underlying id as iOS; Android
provider strings are documented as platform-native persistence; and the APK
overlay copies generated 512px launcher assets instead of decoding the 2048px
branding masters. These corrections passed clean-pin overlay application and
static checks; native compilation and device validation remain pending.

## Android 0.2.5 source parity ready for authorized build (2026-09-08 UTC)

The remaining source-audit rows were closed without building an APK. Deleted
messages now receive their local marker immediately while their eligible
snapshot is retained for reload; edit-revision capture/view/cleanup paths were
reviewed and retained. Canonical proxy settings now synchronize Telegram
Android's existing native `ProxyRotationController`, including the selectable
5/10/15/30/60-second delay. The main proxy menu can stay visible while disabled
and proxy-sponsored promo responses are discarded when requested.

Offline startup uses Telegram Android's existing connection-state behavior:
`ConnectionStateWaitingForNetwork` does not schedule rotation and cancels a
pending rotation runnable, while NagramiX DNS and custom validation execute off
the UI thread. No parallel network monitor was introduced.

The registry and release metadata now target 0.2.5, and the source-parity gate
passes. `.github/workflows/build-android-apk.yml` is restored with
`workflow_dispatch` as its only trigger and includes the parity gate before any
toolchain or build work. It has not been dispatched, in accordance with the
owner's explicit instruction not to build without a separate command. Overlay
application, Python/JSON/YAML validation and repository/generated-tree
`diff --check` passed. Native Gradle/NDK compilation, APK inspection and every
physical-device row remain pending.

Exact next step: wait for explicit authorization to dispatch the manual ARM64
APK workflow. Do not restore publication or claim runtime parity before the
artifact and Samsung/Android device tests pass.

## Android 0.2.4 parity build hold (2026-09-02 UTC)

The owner explicitly prohibited further Android builds or APK publication until the Android implementation reaches iOS 0.2.4 feature parity. Active Android Actions runs `33606103552` and `33605904230` were cancelled, and the obsolete non-current-base APK plus its Android metadata/provenance assets were removed from pre-release `v0.2.4-rc1`. The iOS IPA remains available.

Automatic pull-request Android builds are disabled. `scripts/check_android_release_ready.py` is a mandatory first-stage gate in both the manually dispatched Android build and Android publication workflows. It fails while any feature in `product/features/registry.json` has an Android implementation status other than `implemented`; current expected result is failure because the Android port is incomplete. Do not bypass or weaken this gate to obtain an APK. Implement and review the Android rows against the pinned official Telegram source, update statuses only when durable integrations exist, and build only after all implementation rows pass. Physical-device statuses remain separate and must not be inferred from compilation.

Existing uncommitted work in `android/Sources/NagramiXSettingsActivity.java` and `android/Sources/strings_nagramix.xml` predates this build-hold change and was deliberately preserved without being included in the hold commit. The exact next step is to verify and integrate that settings UI through `android/apply_overlay.py`, then continue feature ports one registry row at a time without triggering an APK build.

## Confirmed product development model (2026-09-02 UTC)

The owner reconfirmed the permanent architecture: NagramiX is one independent, unofficial and non-commercial product with its own features, settings and branding. Shared behavior is designed in `product/`, then implemented independently with Swift/Objective-C in `ios/` and Kotlin/Java in `android/`, using only audited official Telegram pins. iOS is first in implementation priority; Android is second but must not remain a permanently reduced edition. The currently existing official Android GitHub repository was verified as `DrKLO/Telegram`; `TelegramMessenger/Telegram-Android` does not resolve on GitHub and must not be recorded as a fetchable upstream unless Telegram actually creates or moves to it. These rules are now durable in `AGENTS.md` and `product/PRODUCT.md`.

The owner subsequently directed the project to remove the former reference-client concept completely. All names, reference pins, provenance fields and documentation for it were removed from tracked authoritative files. NagramiX now documents only its own product specifications and the audited official Telegram platform bases. Existing settings keys and NagramiX package identifiers were not changed. Verification covered a repository-wide case-insensitive search, environment parsing, Python syntax, workflow YAML and diff checks. No Android APK was built. Next: continue the NagramiX-owned Android settings integration and feature registry ports while the parity gate remains active.

## Android parity implementation resumed (2026-09-02 UTC)

The first Android parity tranche completes the NagramiX-owned settings foundation without building an APK. `android/Sources/NagramiXSettings.kt` now contains every canonical 0.2.4 boolean key/default from `product/SETTINGS.md`; existing keys were preserved. `NagramiXSettingsActivity.java` provides a native Telegram-style settings screen with Interface, Features and Other sections, correct default-aware toggles, and English/Russian resources. `android/apply_overlay.py` copies these sources and uses exact single-occurrence anchors to add the NagramiX row to official Telegram Android's main Settings screen.

Verified: Python syntax, XML parsing/key parity, exact overlay application to a clean detached worktree at the official Android pin, generated-tree `git diff --check`, and inspection of the generated Settings entry/click integration. Not verified: Java/Kotlin compilation, APK packaging, UI rendering, persistence on a physical device, or any switch's downstream feature behavior. Those checks are intentionally deferred because Android builds remain prohibited until implementation parity. Risk: the settings surface is wired, but feature switches other than storage/defaults remain behaviorally inactive until their individual registry ports land. Exact next step: implement the `tabs` registry row against official `DialogsActivity` navigation while keeping the build gate active.

The tabs tranche is now in progress. Exact anchors integrate `interface.hideContactsTab`, `interface.hideCallsTab` and `interface.showTabTitles` with official `MainTabsActivity`: Contacts visibility is controlled by NagramiX, the native Calls/Settings shared position resolves to Settings when Calls is hidden, and all five native main-tab labels can be suppressed. Settings changes publish Telegram's existing `updateInterfaces` notification so the tab bar refreshes without restart. Clean-pin overlay application and generated diff checks passed. Compilation and device behavior remain unverified, and `interface.showSearchTab` still lacks an Android integration, so the registry row correctly remains `in_progress`. Exact next step: implement the separate Search control semantics and audit hidden-Contacts gesture navigation before marking `tabs` implemented.

The Force TCP row now has a NagramiX-owned Android integration. The overlay replaces the official debug-preference read inside `VoIPService` with canonical `calls.forceTcp`, selects Telegram's existing TCP relay endpoint type, disables P2P for that call context, and removes the debug-only per-call toast. Disabled behavior retains the official P2P value and UDP relay endpoint type. Exact anchors, clean-pin application and generated diff checks passed. The registry records source implementation as `implemented`, while compile/device remain `not_started`; no APK was built. Physical incoming/outgoing audio/video calls still require later device validation.

The tabs row is now source-complete and records `implemented`. `interface.showSearchTab` controls the existing native Dialogs action-bar search button only for the main, non-archive, non-selection chat list; search opening and closing retain Telegram's native search pipeline. The button refreshes on the same `updateInterfaces` event and is restored after search closes. The settings event now supplies `MessagesController.UPDATE_MASK_ALL`, fixing the previously detected empty-argument crash risk in `DialogsActivity`. Contacts/Calls visibility and all tab labels remain integrated as described above. Clean-pin exact-anchor application and generated diff checks passed; compile and device statuses remain unverified and no APK was built. Next source port: `round_video_camera`.

The `round_video_camera` row now records Android source implementation as `implemented`. At each fresh `InstantCameraView.showCamera` session, the canonical `videoMessages.useRearCamera` value initializes the existing `isFrontface` selector before either Camera2 or legacy Camera1 session creation. Resume paths preserve the current session; Telegram's native switch button, dual-camera selection, flash, zoom/GL pipeline, orientation and cleanup remain unchanged. Clean-pin overlay application and generated diff checks passed. Compile/device statuses remain unverified and no APK was built. Next: story visibility, camera-swipe, confirmation and repost controls.

The Android `story_controls` row now records source implementation as `implemented`. `interface.hideStories` forces both peer and self story-strip visibility off through the native `updateStoriesVisibility` state machine and refreshes on settings changes. `stories.confirmViewing` intercepts only non-self unread story opens before haptic, media preloading, `StoryViewer.open`, or seen-state work; cancellation does not enter the viewer, while confirmation resumes the exact native path once. `stories.enableRepost` gates Telegram's existing allowRepost calculation without weakening its public/expiry/screenshot/channel eligibility checks. Current official Android has no swipe-to-open-story-camera gesture in its dialogs implementation, so `stories.disableCameraSwipe` is a documented platform non-applicability rather than a no-op patch. Exact anchors, localization parity, clean-pin application and generated diff checks passed. Compile/device status remains unverified; no APK was built. Next: `forward_copy`.

The Android `forward_copy` row now records source implementation as `implemented`. The message context menu adds a distinct localized “Forward without source” action alongside untouched native Forward. Destination selection carries an explicit copy mode. Supported text/web previews, photos, documents, locations and contacts are recreated through `SendMessageParams` rather than `messages.forwardMessages`; replies and TTL are removed, all source entities (including custom emoji) and media spoilers are retained, fresh group ids preserve album grouping, and notify/schedule/repeat/payStars/send-as parameters flow through the native send path. Ephemeral, protected, paid and unsupported media are rejected atomically before sending. The forwarding preview retains copy mode until send and resets it on ordinary forwarding, avoiding stale mode leakage. Exact overlay application, generated diff, localization parity and static path inspection passed. Compilation/device testing remain intentionally deferred and no APK was built. Next: local deleted-message archive and edit history.

## Android workflow removal and PR review follow-up (2026-09-02 UTC)

The owner's stronger release rule supersedes the earlier manual-gate approach:
Android build and publication workflow files are now removed entirely until
source parity. This also makes the review comments about stale artifact binding
and build-workflow path triggers non-applicable while the lock is active. The
settings source mentioned by review is tracked and integrated. The retained
future readiness checker now fails closed for a missing/empty feature list,
missing ids and duplicate ids. No APK or Gradle build was run.

Current source status: tabs, round-video camera, stories, copy-as-new and Force
TCP are implemented but not compiled/device-tested; icons are in progress;
deleted-message archive, edit history, DNS/DoH, proxy failover, profile data and
offline startup remain. Exact next step: implement the account-local Android
message archive and observed edit history, including exclusions and chat UI,
while keeping Android workflows absent.

## Android message archive tranche (2026-09-02 UTC)

`NagramiXMessageArchive.java` now provides an account-scoped SQLite snapshot
store on the official Android base. Incoming cloud messages are captured from
the native storage ingress without fetching media. Outgoing, self, verification,
secret-dialog, protected, paid, TTL, expiring and secret-media messages are
excluded. Server deletions mark existing snapshots; an open chat preserves an
eligible deleted object, and later history loads merge persisted deleted
snapshots with a localized marker. Logout clears the account archive.

Observed edits in an open chat capture the previous serialized message only
when text/entities/media content changes. A native context-menu action lists
captured revisions and allows copying the selected text. Both registry rows are
only `in_progress`: compile validation is intentionally prohibited, deletion
coverage for every non-open channel/global-id path still needs audit, synthetic
message action restrictions need hardening, and the settings UI still needs a
confirmed archive-cleanup action. Exact-anchor application and generated-tree
diff checks pass; no APK was built. Next: close those gaps before advancing
either archive row to `implemented`.

The follow-up closes part of that backlog: storage ingress now detects content
changes globally, records the previous serialized message and updates the
current snapshot, so edit capture is not limited to an open chat. The settings
screen has a destructive, confirmed per-account archive cleanup action. Locally
merged deleted snapshots are forced read and non-forwardable, and Delete removes
only the local archive row instead of invoking a server action. Both rows remain
`in_progress` pending a complete audit of other context actions and every
channel/global-id deletion path. Static overlay/localization/diff checks pass;
no Gradle or APK command was run.

## Android profile information (2026-09-02 UTC)

The `profile_info` source row is implemented. User, group and channel profiles
conditionally expose a copyable numeric peer id through Telegram's native
detail cell and copy bulletin. User profiles use a NagramiX-owned metadata
helper with the same broad, explicitly approximate registration-year ranges as
iOS. `UserCell` appends a theme-colored group glyph only for Telegram users
whose real `mutual_contact` field is true, excluding self, bots and deleted
accounts. The shared contract is now durable in
`product/features/profile-info.md`. Exact overlay application and generated
diff checks passed. Compilation, rendering, clipboard behavior and physical
device verification remain intentionally pending; no APK was built. Next:
complete the seven Android alternate launcher icons, then DNS/DoH.

## Android application icons (2026-09-02 UTC)

The `icons` source row is implemented. All eight NagramiX PNG sources are now
owned under `android/branding/AppIcons/`. The overlay copies them to Android
resources, replaces the six official launcher choices with eight NagramiX-owned
`LauncherIconController` entries, and exact-range replaces the launcher aliases
in the official main manifest. The first alias is enabled by default and the
existing native Telegram icon selector/switching lifecycle is retained. Static
validation confirms exactly eight enum entries, aliases and generated resource
files. Compilation, launcher refresh behavior and Samsung home-screen rendering
remain pending under the no-build rule. No APK was built. Next: DNS provider and
custom DoH integration.

## Android DNS and custom DoH (2026-09-02 UTC)

The `dns_doh` Android source row is implemented without producing an APK.
`NagramiXDnsResolver` provides the same system, Google, Quad9, AdGuard, Mullvad,
Cloudflare and custom-provider contract as iOS using bounded RFC 8484 wire-format
POST requests. It validates response ids, status and address records, attempts A
then AAAA, and deliberately does not fall back to system DNS after a selected
DoH provider fails. The official `ConnectionsManager` resolver path is selected
through exact anchors and its result cache is cleared whenever the provider
changes.

The native NagramiX settings screen now exposes the provider selector and a
custom HTTPS URL editor. Custom URLs are syntax checked and must resolve
`example.com` before persistence. The cross-platform behavior is documented in
`product/features/dns-doh.md`. Static source, resource, exact-anchor clean-pin
overlay and generated-tree diff validation passed. Native compilation, real provider
availability, captive-portal behavior and physical-device recovery remain
unverified under the Android no-build rule. No APK was built. Next: implement
proxy checking/failover/button behavior and offline/proxy startup hardening,
then finish the message archive action/deletion-path audit.

## Android outgoing-call confirmation (2026-09-07 UTC)

A parity-ledger omission was corrected: `calls.confirmOutgoing` is now its own
release-gated feature row and has a shared product contract. The official
one-to-one `VoIPHelper.startCall` path preserves its frozen-account, privacy and
offline checks, then shows a native NagramiX confirmation for outgoing audio or
video calls when enabled. Confirming resumes the same permission/initiation path
exactly once through a private confirmed overload; cancellation starts nothing.
Incoming and group calls are untouched. Static syntax, localization, registry,
exact-anchor clean-pin application and generated-tree diff validation passed.
Compilation and physical call testing remain deferred
under the no-build rule. No APK was built. Next: native proxy check/failover and
visibility behavior, then offline startup and archive audits.

## iOS settings category width correction (2026-09-07 UTC)

The owner reconfirmed that the Interface / Features / Other category control
must begin after the circular Back control and extend to the same trailing inset
as the settings cards. Equal internal tab widths alone did not satisfy this:
UIKit's navigation title slot reserves symmetric space for the Back item and
therefore left an unnecessary empty area on the right.

The NagramiX-only `equalSectionControl` overlay now keeps its post-Back origin,
computes the available width to the window's trailing safe/content inset, draws
the glass panel into that otherwise unused navigation space, divides the result
into three equal hit targets, and extends hit testing across the complete panel.
Ordinary Telegram `.sectionControl` titles retain their existing fit layout.
The intended geometry is recorded in
`docs/mockups/settings-category-full-width.svg` and its rendered PNG preview.

Python syntax, exact application to a clean pinned Telegram-iOS 12.9.2 checkout,
generated-tree `git diff --check`, and visual inspection of the mockup passed.
Native Xcode/Bazel compilation and physical-iPhone layout/touch verification
remain pending. Exact next step: run the authoritative iOS workflow when builds
are permitted, then verify narrow displays, Dynamic Type, all three hit regions,
rotation/safe areas and the absence of clipping on a physical iPhone.
