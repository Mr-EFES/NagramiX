# NagramiX AI Handoff

## Last updated

- Date: 2026-09-01 (UTC).
- Agent: Codex, primary agent.
- Repository root used for this handoff: `/workspace/NagramiX`.

## Current project state

NagramiX is an overlay monorepo for independent Telegram clients for iOS and Android. It does not track either complete upstream tree. CI applies the iOS overlay to pinned Telegram-iOS 12.9.2 and the Android overlay to pinned NagramX 1258.

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

The message context-menu forward modes were corrected locally in the uncommitted `nagramix/apply_features.py` change. The two existing actions already passed explicit `ChatInterfaceForwardOptionsState` values, but `ChatControllerForwardMessages.swift` discarded that outer value after destination selection and used only the peer picker's `forwardOptions`. The overlay now uses `options ?? forwardOptions`: NagramiX's explicit mode wins, while ordinary Telegram forwarding with `options == nil` retains the picker's standard behavior. “Forward without author” uses Telegram's existing `ForwardOptionsMessageAttribute(hideNames: true)`, which becomes the native `messages.forwardMessages` bit 11 (`drop_author`) and suppresses local `forwardInfo`; it does not rebuild or modify `MessageObject` instances. Text entities, media/captions, custom emoji, message order and album grouping remain in the native forwarding pipeline. Secret chats, paid media and non-Premium rich messages disable the anonymous action, while the existing action-availability logic continues to block protected and self-destruct content. The distinct icon reuses Telegram's tintable `message_preview_person_off` animation.

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
- Continued fixes for story-view confirmation, rear-camera video messages and zoom behavior through exact upstream patches in `nagramix/apply_features.py`.
- Kept the clean-install defaults for Russian localization, dark theme and the built-in game wallpaper, without intentionally overwriting established user choices.
- The previous 0.1.9/0.2.0 work introduced the DNS selector and DoH resolver path, custom DoH validation, proxy auto-switch controller, persistent proxy button, tab controls, story controls, eight application icons and Russian Debug-menu localization.

These statements describe implemented code and build history. They do not imply that every runtime scenario has been verified on the latest physical-device build.

## Completed in the 0.2.2 build

The earlier forwarding, round-video and proxy work plus the deleted-message/edit-history implementation are committed and included in the successful 0.2.2 native build. The durable feature sources are under `nagramix/`, not in a generated validation tree:

- `nagramix/Sources/TelegramCore/NagramiXMessageArchive.swift` — new account-owned, asynchronous local snapshot archive. It stores only received incoming cloud messages, text/caption entities, safe image/file references and peer data; it excludes secret chats, verification-code chats, copy-protected peers/messages, autoremove/autoclear/view-once/ephemeral content and paid media.
- `nagramix/Sources/NagramiXCore/Sources/NagramiXTabSettings.swift` — persists `nagramix.messages.showDeletedMessages` and `nagramix.messages.editHistory`, both defaulting to `false`.
- `nagramix/Sources/SettingsUI/NagramiXSettingsController.swift` — adds the FEATURES / MESSAGES switches, explanatory rows and confirmed local-archive cleanup action.
- `nagramix/Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift` and `Resources/{en,ru}.lproj/Localizable.strings` — add all message-archive labels and actions without Swift string literals.
- `nagramix/apply_features.py` — copies the archive into TelegramCore and uniquely anchors integration into Account, state mutation, interactive deletion, chat-history rendering, bubble status and the message context menu. It also restores a missing CLI entry point so `python nagramix/apply_features.py --telegram-dir ...` actually applies the overlay.
- `nagramix/Sources/SettingsUI/ProxyListNagramiXBlock.swift.inc` — contains the committed proxy batch-check work.

The archive is keyed by peer/message namespace/message id and stored as `nagramix-message-archive.json` inside the account `basePath`. Telegram's existing `managedCleanupAccounts` removes the complete `account-*` directory after logout/removal, so the archive follows account data cleanup. Synthetic deleted messages are built only for the active `MessageHistoryView` conversion and are never inserted into Postbox; they therefore do not participate in unread counts, notifications, chat-list ordering/last-message, search, read state or server actions. Context actions on synthetic messages are restricted to Copy, Edit History and local Delete.

Local validation passed: Python compilation, repository `git diff --check`, duplicate/missing localization checks, clean full overlay application to Telegram-iOS SHA `6ad963e5b62d354da79040f388ae2b9132fb17b8`, unique new anchors and generated-tree `git diff --check`. Native macOS/Xcode/Bazel compilation then passed in run `33094859022`. Physical-iPhone runtime and crash regression tests remain pending and must not be inferred from compile success.

The pre-existing `README.md` modification is unrelated and must not be folded into these feature changes without separate review. `AGENTS.md`, `docs/AI_HANDOFF.md`, validation checkouts, logs and artifacts remain untracked; the new archive source is also currently untracked in the dirty worktree and must be included when the intended overlay change is eventually committed. Validation copies are not authoritative feature sources.

## Important architecture/context

1. **Overlay, not full fork.** `nagramix/apply_overlay.py` is the CI entry point. It generates a temporary configuration from environment secrets, changes pinned branding/build anchors, creates app-icon assets and invokes `apply_features(source)`.
2. **Pinned upstreams.** `nagramix/upstream.env` pins Telegram-iOS commit `6ad963e5b62d354da79040f388ae2b9132fb17b8`; `android/upstream.env` pins NagramX tag 1258 at commit `ee899eff5a4980ae4f9eca7f60227029b95cbe07`.
3. **Fail-fast patching.** `nagramix/apply_features.py` uses exact single-occurrence anchors and ranges. A missing anchor aborts the overlay instead of silently producing a partially branded or partially functional build. Updating Telegram-iOS requires auditing these patches.
4. **Isolated custom code.** Custom Swift/Objective-C sources live under `nagramix/Sources/` and are copied into the temporary Telegram tree. Bazel dependencies and small upstream integrations are then added by the patcher.
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
- `nagramix/upstream.env` — authoritative pinned Telegram-iOS SHA/version and NagramX reference.
- `nagramix/configuration.template.json` — non-secret build configuration template and NagramiX bundle metadata.
- `nagramix/apply_overlay.py` — branding/configuration/icon orchestration and feature-overlay entry point.
- `nagramix/apply_features.py` — all exact upstream integration patches; highest-risk maintenance file.
- `nagramix/generate_fake_profiles.py` — temporary self-signed profile generation on macOS.
- `scripts/package_unsigned_ipa.sh` — unsigned IPA packaging and final metadata checks.
- `nagramix/Sources/NagramiXCore/Sources/NagramiXTabSettings.swift` — typed DNS provider, persistent feature settings, defaults, migration and notifications.
- `nagramix/Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift` — NagramiX localization accessors layered on Telegram presentation data.
- `nagramix/Sources/NagramiXCore/Resources/{en,ru}.lproj/Localizable.strings` — English and Russian NagramiX strings.
- `nagramix/Sources/SettingsUI/NagramiXSettingsController.swift` — main NagramiX settings UI.
- `nagramix/Sources/SettingsUI/NagramiXCustomDohController.swift` — HTTPS DoH URL validation/edit UI.
- `nagramix/Sources/SettingsUI/ProxyListNagramiXBlock.swift.inc` — replacement proxy screen block injected into pinned SettingsUI.
- `nagramix/Sources/TelegramCore/NagramiXProxyFailoverController.swift` — runtime proxy failure monitor and failover coordinator.
- `nagramix/Sources/TelegramCore/NagramiXMessageArchive.swift` — account-scoped local deleted-message and edit-revision snapshot service.
- `nagramix/Sources/MtProtoKit/NagramiXDNSResolver.{h,m}` — DNS-over-HTTPS implementation for MtProtoKit integration.
- `nagramix/branding/AppIcons/1.png` through `8.png` — authoritative app-icon source images.

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
- `nagramix/apply_features.py` is large and tightly coupled to the pinned upstream text. It is intentionally fragile across upstream revisions.
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

1. Read `nagramix/upstream.env`.
2. Check out Telegram-iOS with recursive submodules at the pinned SHA.
3. Verify `versions.json` reports Telegram `12.9.2` and select its required Xcode.
4. Run:

   ```bash
   python3 nagramix/apply_overlay.py \
     --source Telegram-iOS \
     --configuration "$RUNNER_TEMP/nagramix-configuration.json"
   ```

5. Generate temporary build-only profiles with `nagramix/generate_fake_profiles.py`.
6. Build Telegram-iOS with its native `build-system/Make/Make.py`, configuration `release_arm64`, through Bazel.
7. Package and validate the unsigned app with `scripts/package_unsigned_ipa.sh`.
8. Upload `NagramiX-0.2.3-unsigned.ipa` and `BUILD-PROVENANCE.txt` as an Actions artifact.

The workflow can be started with GitHub Actions `workflow_dispatch` or by a pull request change under its configured paths.

### Safe local static checks

From the repository root, Windows/macOS/Linux agents can run:

```text
python -m py_compile nagramix/apply_overlay.py nagramix/apply_features.py nagramix/generate_fake_profiles.py
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

- `nagramix/Sources/TelegramCore/NagramiXMessageArchive.swift` — new persistent account-local snapshot service and synthetic deleted-message model.
- `nagramix/Sources/NagramiXCore/Sources/NagramiXTabSettings.swift` — adds the two default-off persisted message switches while retaining earlier settings work.
- `nagramix/Sources/SettingsUI/NagramiXSettingsController.swift` — adds the FEATURES / MESSAGES controls and confirmed archive cleanup.
- `nagramix/Sources/NagramiXCore/Sources/NagramiXPresentationStrings.swift` and `Resources/{en,ru}.lproj/Localizable.strings` — add message-archive UI strings while retaining prior proxy strings.
- `nagramix/apply_features.py` — integrates capture-before-edit/delete, local-delete suppression, synthetic history entries, Deleted bubble status and formatted Edit History context action; it also restores the executable CLI footer and enforces unique anchors for the new integration.
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

Authoritative changed files for this fix are `nagramix/Sources/TelegramCore/NagramiXProxyFailoverController.swift`, `nagramix/Sources/MtProtoKit/NagramiXDNSResolver.m`, `nagramix/apply_features.py` and this handoff. The clean generated validation tree is `.codex-validation-offline-copy4-0.2.3` and must not be committed.

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

The repository now contains a second platform overlay under `android/`. NagramX tag 1258 is pinned to exact commit `ee899eff5a4980ae4f9eca7f60227029b95cbe07`; the full 30,000-file upstream tree remains external. `android/apply_overlay.py` rejects any other commit or changed exact anchor, then applies version 0.2.4, package `com.mr_efes.nagramix`, NagramiX branding, debug-signing compatibility and aligned clean-install defaults. It also verifies source anchors for deleted messages, edit history, stories, copy/forward modes, round-video selection, custom DoH and Force TCP.

`.github/workflows/build-android-apk.yml` checks out the pinned Android source recursively, applies the overlay, uses the existing Telegram API repository secrets, installs JDK/SDK/NDK tooling, builds an ARM64 debug APK, validates package/version/signature metadata, records SHA-256/provenance and uploads the test artifact. The generated debug signing key is not a stable production identity; users may need to uninstall a differently signed earlier build.

`docs/ANDROID-FUNCTION-PARITY.md` is the durable parity matrix. Source-level availability or a successful Gradle build must not be presented as physical-device verification. Current verification: overlay application to a clean pinned checkout, exact anchors, Python compilation, YAML parsing and overlay/generated-tree `git diff --check` pass. Native Gradle/NDK CI and all physical-device rows remain pending. Exact next step: push the branch, let the Android workflow build the APK, inspect its metadata/signature/SHA-256, then install it on an ARM64 Android device and record every matrix result or mismatch.

The first Android CI attempt, run `33543465270`, reached the SDK installation step and failed before compilation because `sdkmanager` does not expose `platforms;android-37`; pinned NagramX uses the upstream-tested preview package name `platforms;android-37.0`. The workflow was corrected to request that exact package. No APK was produced by the failed attempt.
