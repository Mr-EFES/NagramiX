# NagramiX AI Handoff

## Last updated

- Date: 2026-09-12 (UTC).
- Agent: Codex, primary agent.
- Repository root used for this handoff: `/workspace/NagramiX`.

## 0.2.7 iOS-only build-ready preparation (2026-09-12 UTC)

The owner requested a clean single-branch repository prepared for, but not yet running, the NagramiX 0.2.7 IPA build. The active branch is now named `main`. The Android overlay, branding, parity document and Android build/publish workflows were removed. Current identity, bootstrap, product, compatibility, settings, upstream and feature-registry documents now describe iPhone/iOS only; older release notes and older handoff sections retain historical facts only.

GitHub Actions and Codemagic version metadata, the release publisher, README, feature registry and `product/releases/0.2.7.md` target 0.2.7. The registry compile/device fields are deliberately `not_started` until the new macOS build and physical-iPhone acceptance actually occur. The refreshed `AppIcons/1.png` through `8.png` remain the authoritative set, with icon 1 used as the primary icon.

Static repository checks are recorded in the latest commit. A fresh clean-overlay application and native macOS build remain part of the authoritative workflow. No 0.2.7 workflow was dispatched because the owner asked to give a separate build command. Exact next step: after the owner's command, push `main` if authenticated GitHub access is available, dispatch `.github/workflows/build-unsigned-ipa.yml` from that exact commit, wait for compilation/package/upload, and report the run and artifact without claiming device acceptance.

## Main-branch consolidation and scope correction (2026-09-10 UTC)

The repository's local `main` branch was created from and tracks `origin/main`, then fast-forwarded from the former 0.2.5 tip `f5e2b9e` through the complete published 0.2.6 line ending at `1f05146`. This brings the iOS 0.2.6 build/publication checkpoint, the Android 0.2.6 implementation, all compiler-guided Android fixes, and the Android publication record onto one linear main-branch history. The previous squashed `work` attempt was preserved as a separate local branch rather than merged, because its product tree duplicates the verified release line and lacks the individual compiler-fix checkpoints.

The 0.2.6 release wording was also corrected: its 14 entries are the tracked and auditable 0.2.6 contract, **not** proof that every request ever made by the owner was captured or delivered. Earlier statements implying complete fulfillment beyond that written contract were too broad. Unknown or omitted requests must first be reconciled against the owner's original list, added to product specifications and the feature registry, and then implemented and tested honestly; they must not be inferred from a successful build or from the 0.2.6 version number.

Verification for this consolidation includes remote-ref/ancestry inspection, confirmation that the chosen 0.2.6 Android-release tip contains the old `origin/main`, comparison against the other 0.2.6 branch tips, JSON/YAML/Python/shell/static overlay checks, and repository whitespace checks. Existing native build evidence remains the successful published 0.2.6 workflow history recorded below. No new native build or physical-device test was performed during consolidation.

On 2026-09-11 the owner set a main-only, iOS-first development policy. The consolidated history and policy commit were published to `origin/main`; the five superseded open pull requests were closed and all ten obsolete remote development branches were removed after the required 0.2.6 results had been consolidated. `main` is now the repository's only remote branch. Android source is retained, but new Android implementation, builds and device testing are paused until the matching iOS behavior is specified, implemented and accepted. The concise next-iOS-build inventory and remaining acceptance work are recorded in `product/releases/NEXT-IOS.md`.

Exact next step: rebuild the unsigned IPA from the exact `main` SHA, perform physical-iPhone acceptance, and inventory any owner request missing from the product specifications before promising a later release scope.

## iOS 0.2.6 acceptance reset (2026-09-11 UTC)

The owner decided that the previously published `v0.2.6-rc1` must not represent the accepted iPhone release. The GitHub release was already absent when checked; its remaining remote tag was deleted. An initial rebuild dispatch from `d8d54fe` was canceled before compilation so the acceptance-reset documentation could be included in provenance. Replacement run `34586208208` from `8b92946` completed successfully through native ARM64 compilation, unsigned packaging, provenance generation and artifact upload. Its IPA remains an unaccepted Actions test artifact; publish 0.2.6 only after physical-iPhone acceptance. Older 0.2.4 and 0.2.5 tags remain historical records and were not removed.

The owner subsequently established exact release numbering with no RC suffixes: the accepted release tags are `v0.2.6`, then `v0.2.7`, and so on. Publisher defaults, release titles and current release documentation now follow that policy. Build artifacts remain unpublished test candidates until iPhone acceptance; successful acceptance permits publication under the exact `v0.2.6` tag.

## Current project state

NagramiX is an overlay monorepo for independent Telegram clients for iOS and Android. It does not track either complete upstream tree. CI applies the iOS overlay to pinned official Telegram-iOS 12.9.2 and the Android overlay to pinned official Telegram Android 12.10.1. iOS is the product priority; NagramX 1258 is an idea reference only.

- Active integration branch: local `main`, containing the complete linear 0.2.6 history through the consolidation commit recorded above.
- Configured origin: `https://github.com/Mr-EFES/NagramiX.git`; GitHub CLI device authentication for account `Mr-EFES` was confirmed before publication.
- Latest confirmed native iOS build: GitHub Actions run `34586208208`, successful for commit `8b92946`; its unsigned IPA and provenance are retained as Actions artifact `NagramiX-0.2.6-unsigned-arm64` for physical-iPhone acceptance and have not been published as a release.
- Latest confirmed native Android build: GitHub Actions run `34436394652`, successful for commit `ac3b270`; publisher run `34438808463` attached the ARM64 debug APK and verification files to the same pre-release.
- Native compilation is recorded as passed for the 14 documented 0.2.6 rows. iPhone device status remains pending and Android device status remains not started; do not present either build as physical-device acceptance.

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
- `ios/upstream.env` — authoritative pinned Telegram-iOS SHA/version and NagramX reference.
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

The repository now contains a second platform overlay under `android/`. NagramX tag 1258 is pinned to exact commit `ee899eff5a4980ae4f9eca7f60227029b95cbe07`; the full 30,000-file upstream tree remains external. `android/apply_overlay.py` rejects any other commit or changed exact anchor, then applies version 0.2.4, package `com.mr_efes.nagramix`, NagramiX branding, debug-signing compatibility and aligned clean-install defaults. It also verifies source anchors for deleted messages, edit history, stories, copy/forward modes, round-video selection, custom DoH and Force TCP.

`.github/workflows/build-android-apk.yml` checks out the pinned Android source recursively, applies the overlay, uses the existing Telegram API repository secrets, installs JDK/SDK/NDK tooling, builds an ARM64 debug APK, validates package/version/signature metadata, records SHA-256/provenance and uploads the test artifact. The generated debug signing key is not a stable production identity; users may need to uninstall a differently signed earlier build.

`docs/ANDROID-FUNCTION-PARITY.md` is the durable parity matrix. Source-level availability or a successful Gradle build must not be presented as physical-device verification. Current verification: overlay application to a clean pinned checkout, exact anchors, Python compilation, YAML parsing and overlay/generated-tree `git diff --check` pass. Native Gradle/NDK CI and all physical-device rows remain pending. Exact next step: push the branch, let the Android workflow build the APK, inspect its metadata/signature/SHA-256, then install it on an ARM64 Android device and record every matrix result or mismatch.

The first Android CI attempt, run `33543465270`, reached the SDK installation step and failed before compilation because `sdkmanager` does not expose `platforms;android-37`; pinned NagramX uses the upstream-tested preview package name `platforms;android-37.0`. The workflow was corrected to request that exact package. No APK was produced by the failed attempt.

### Android 0.2.4 native CI result

Android run `33543742039` succeeded for commit `55211affebbb12a430d07772d340e61f73b082b5`. Gradle completed in 29m10s and produced artifact `NagramiX-0.2.4-android-arm64` (artifact id `9815786610`, archive size 67,568,542 bytes). Validated APK metadata: package `com.mr_efes.nagramix`, version code `204`, build version `0.2.4-f828a0c`, compile SDK 37. `apksigner` verified APK Signature Scheme v2 with the ephemeral Android Debug certificate; certificate SHA-256 is `f35b50bf9de6e1fb3780eaa945d10e57343c685cf605973f67d57245c5c4a7b3`. APK SHA-256 is `b6347954016ba9e5d37ca34e6a80d793d0dafa3b52e91b7bc847c92066639937`. Compilation and packaging are proven; physical-device functionality remains pending.

`.github/workflows/publish-android-prerelease.yml` transfers the validated Actions artifact to an existing GitHub pre-release without exposing credentials or depending on a local artifact CDN download. After merge, dispatch it for run `33543742039`, artifact `NagramiX-0.2.4-android-arm64`, tag `v0.2.4-rc1`. The exact next step after publication is to install the APK on an ARM64 Android device and record results in `docs/ANDROID-FUNCTION-PARITY.md`.

The first Android publisher run `33547055308` verified the complete APK ZIP but failed its checksum command because the checksum file stores a basename while the workflow ran from the repository root. The validation was corrected to execute `sha256sum --check` inside `release-assets`; the downloaded APK itself was not implicated.

Android publisher run `33547148058` then passed ZIP integrity, SHA-256 verification and release upload. GitHub pre-release `v0.2.4-rc1` now contains `NagramiX-0.2.4-android-arm64.apk` (77,171,492 bytes, SHA-256 `b6347954016ba9e5d37ca34e6a80d793d0dafa3b52e91b7bc847c92066639937`) alongside the iOS IPA and Android metadata, signature, checksum and provenance files. PRs `#4` and `#5` are merged. Remaining work is exclusively physical-device Android testing and any fixes it reveals; record results in `docs/ANDROID-FUNCTION-PARITY.md` without upgrading Pending rows based on compilation alone.

## Android architecture correction: official Telegram base (2026-09-01)

The product owner clarified the authoritative architecture: NagramiX is an independent application; iOS is the priority platform, Android is a first-class secondary platform, and both start from official Telegram repositories. Shared product ideas may come from NagramX 1258, but NagramX source must not be the Android base or be compiled into NagramiX. iOS features are implemented natively in Swift/Objective-C and Android counterparts in NagramiX-owned Kotlin/Java.

The earlier NagramX-based Android artifact and parity claims are superseded and must not be treated as the independent Android client. The replacement pin is official `DrKLO/Telegram` commit `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, whose `gradle.properties` reports 12.10.1 (7038). `android/apply_overlay.py` was rewritten for this official tree: it sets independent version/package metadata, injects NagramiX branding and a Kotlin-owned settings namespace, uses repository-secret Telegram API credentials through generated BuildConfig fields, disables official-only update/passkey behavior, configures independent debug signing and limits the development APK to ARM64.

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

Static verification completed: official upstream audit with `--require-current`, Android overlay application to a clean official checkout, Python compilation, JSON parsing, workflow YAML parsing, embedded shell syntax and repository/generated-tree `git diff --check`. Native IPA was not rebuilt because iOS product code did not change. The restructured current-official Android APK requires a fresh GitHub Actions build before the obsolete NagramX-based APK release asset can be replaced. Physical-device validation remains pending.

Exact next step: authenticate GitHub CLI, synchronize with `origin/main`, push this focused restructuring commit, create a PR, run Android CI, inspect APK metadata/signature/provenance, replace the old Android release asset only after success, then continue feature ports from `product/features/registry.json` in iOS-priority order.

## PR #7 review follow-up (2026-09-02 UTC)

Addressed every inline review item: Android now uses canonical `interface.hideStories`; the shared outgoing-call confirmation default matches the shipped iOS `true`; Android documentation names official Telegram 12.10.1; icon status remains `not_started` until compilation; scheduled upstream checks fail when pins become stale; and the launcher source is owned by `android/branding`. The Android overlay also removes the Google Services plugin from the repackaged application, fixing CI's `processAfatDebugGoogleServices` failure for the independent package id.

Changed files are the six reviewed files, `android/branding/AppIcons/1.png`, `android/apply_overlay.py`, and this handoff. Static validation passed before commit. Native Android CI is rerunning; physical Android and iPhone testing remains pending. Exact next step after a green Android build is to keep implementing the product registry rather than publish a parity APK.

Sparse clean-pin overlay validation initially found a trailing blank line after plugin removal. The exact anchor was widened to consume the separator plus plugin line; the rerun applied successfully and generated-tree `git diff --check` passed.

## iOS 0.2.6 implementation session (2026-09-09 UTC)

The iOS release metadata now targets 0.2.6. Story behavior settings are consolidated under Features / Stories without changing any persisted key, Force TCP is displayed under Other while retaining `nagramix.calls.forceTcp` and its existing VoIP backend, and the deleted-message/edit-history secondary text is explicitly marked Experimental in English and Russian. The broadcast-wide layout overlay now restores the shared adaptive content width after Telegram's content-type-specific clamps, so ordinary broadcast posts feed one width into their native content nodes while non-broadcast chats preserve upstream geometry.

The existing 0.2.5 iOS overlay was inspected against a clean pinned Telegram-iOS 12.9.2 checkout. It already routes multi-destination Copy as New through Telegram's standard `.generic`, `.silent`, `.schedule`, and `.whenOnline` transformations, uses `OutgoingScheduleInfoMessageAttribute`, and keeps copied values as `.message`; clean-install Russian and `.nightAccent` defaults are also already present. The clean overlay application passed after the 0.2.6 changes.

The remaining iOS source blocks were completed in the follow-up. `StoryContainerScreen` now gates explicit item navigation, automatic/tap navigation routed through it, and peer swipes against the exact target `EngineStoryId` before changing the content context. The fullscreen controller uses Telegram photo/video thumbnail signals without starting playback; confirmation grants a one-story approval id, and the native `markAsSeen` callback rejects unapproved external stories. Own stories and setting-off behavior remain native. Cancellation does not execute the navigation action.

Select From Author now uses `TelegramEngine.Messages.searchMessages` with `.peer(peerId:fromId:threadId:)`, feeds each returned `SearchMessagesState` into the next request until `result.completed`, and selects the accumulated engine result ids. A dedicated `MetaDisposable`, generation, active-operation guard, cancellable Telegram loading overlay, and peer/thread checks protect cancellation and controller lifecycle. Display names and forward metadata are not used as identity.

Clean overlay application, generated-tree `diff --check`, Python compilation, and generated-source invariants passed. Native macOS/Bazel compilation and physical-device acceptance remain pending. No Android parity work was started, per the owner-requested iOS-first sequence. Exact next step: port the accepted 0.2.6 product behavior natively to the official Android base, then run platform builds and physical-device matrices.

## Android 0.2.6 parity continuation (2026-09-09 UTC)

Android release metadata now targets 0.2.6/206. The NagramiX-owned settings namespace gained the existing product keys for story swipe, per-story confirmation, repost and wide broadcast posts without renaming prior keys. The official `LocaleController` initialization now chooses built-in `ru` only when Telegram has no explicit `language` preference, preserving manual choices and logout behavior while keeping IntroActivity's native system-language suggestion. The official `Theme` initialization similarly selects the existing `Dark Blue` ThemeInfo/accent 9 only when no explicit day theme exists, before the first UI is rendered; saved themes remain authoritative and auto-night support is untouched.

A clean application to official Telegram Android 12.10.1 passed, along with Python compilation and generated-tree `diff --check`. Native Gradle/NDK compilation and physical-device clean-install/update checks remain pending. Most Android parity rows—including StoryViewer gating, settings UI, wide message-cell layout, Copy as New, archive/edit history, Force TCP UI/backend, and Select From Author—are still not ported. Exact next step: implement the Android NagramiX settings surface and StoryViewer per-target gate using the inspected official classes, then continue message sending/layout/search integrations before any release build.

## Android 0.2.6 settings surface (2026-09-09 UTC)

A NagramiX entry is now integrated into official Telegram's SettingsActivity using its existing SettingCell/presentSettingFragment path. The NagramiX-owned BaseFragment provides equal-width Interface, Features and Other selectors and uses Telegram HeaderCell, TextCheckCell and TextInfoPrivacyCell components with Theme colors. Features / Stories contains exactly hide stories, disable recording swipe, per-story confirmation and repost; Other contains the single existing Force TCP key; deleted messages and edit history use localized Experimental secondary text. English and Russian resources are copied through the exact overlay.

This completes the Android settings placement/UI portion only. The switches persist stable product keys, but most corresponding Android behaviors are not connected yet. StoryViewer gating, wide ChatMessageCell geometry, Copy as New/send options, archive/edit-history storage/UI, Force TCP transport, Select From Author pagination and the remaining parity features are still pending. Clean overlay application, XML parsing and generated-tree `diff --check` passed; native compilation was not run. Exact next step: implement the per-story pre-navigation/read gate in official StoryViewer/PeerStoriesView and bind the settings to their native behavior.

## Android per-story privacy gate (2026-09-09 UTC)

The official Android `PeerStoriesView.updatePosition` is now the common pre-bind gate for every selected target, including initial bind, tap/automatic next/previous and peer-page changes. Before `currentStory` changes, media/player setup runs or `CurrentStory.checkSendView` can call `StoriesController.markStoryAsRead`, it asks `StoryViewer` to approve the exact `(dialogId, storyId)`. Approval is consumed once on the re-entered bind. Own stories and setting-off behavior bypass the gate. Cancel restores the already bound selection, or closes an initial viewer with no committed story.

`NagramiXStoryConfirmationView` is a fullscreen child of Telegram's StoryViewer container, not an AlertDialog. It uses `StoriesUtilities.setImage` with `BackupImageView`'s native blurred receiver for cached photo/video thumbnails, a Theme-derived scrim and controls, dynamic user/channel title, a large View button and close action. StoryViewer Back cancels the overlay first. No player, audio or timer is created by the confirmation view.

Clean exact-overlay application and generated-tree `diff --check` pass. Native Java/Kotlin/Gradle compilation and device acceptance remain pending. Hide-story, recording-swipe and repost switches still require behavior wiring; other Android parity blocks also remain pending.

## Android Story gate and Force TCP integration (2026-09-09 UTC)

Android now has a source-level per-target Story gate at `PeerStoriesView.updatePosition` for active same-peer navigation and at `setActive` for preloaded peer-page activation. Both execute before `currentStory` replacement, player request and `CurrentStory.checkSendView`/`StoriesController.markStoryAsRead`. `StoryViewer` owns a one-use `(dialogId, storyId)` approval and handles Back; the fullscreen NagramiX view uses Telegram's blurred `BackupImageView`/`StoriesUtilities.setImage` thumbnail path, dynamic peer names, Theme colors, close and confirm controls. Cancellation leaves the committed story unchanged or closes an initial viewer.

Force TCP now reuses official `VoIPService`'s existing `forceTcp` endpoint-type branch. The stable NagramiX preference is ORed with Telegram's debug preference at call context construction; when disabled upstream behavior is unchanged, and no MTProto/message transport is affected.

Clean exact-overlay application, XML parsing, Python compilation, generated pre-bind/read-gate invariants and generated-tree `diff --check` pass. Native Gradle compilation and device tests remain pending. Hide Stories, recording swipe, repost, wide messages, Copy as New, archive/edit history and Select From Author still require Android behavior ports.

## Android Story controls completion (2026-09-09 UTC)

The remaining Story switches are now connected to official Android behavior. `DialogsActivity.updateStoriesVisibility` forces both ordinary and self-only tray visibility false when `interface.hideStories` is enabled. `DialogStoriesCell.openStoryForCell` rejects only the overscroll-to-recorder path for a self cell when `stories.disableCameraSwipe` is enabled, leaving explicit recorder buttons intact. `PeerStoriesView` retains all upstream share/public/channel checks and additionally requires `stories.enableRepost` before exposing the native repost control. No duplicate story UI or player implementation was added.

The clean official-base overlay and generated-tree `diff --check` pass. Story controls are source-complete but native/device validation is pending. Wide message layout, Copy as New with send options, archive/edit history, Select From Author and other parity rows remain incomplete.

## Android Copy as New send-options integration (2026-09-09 UTC)

Android now exposes “Forward without” / “Переслать без” beside Telegram's ordinary Forward action for both a single message and action-mode multi-selection. The destination selection remains Telegram's `DialogsActivity`; NagramiX carries only a transient operation flag into `ChatActivity.didSelectDialogs`. Multi-destination sends pass that flag as the existing `SendMessagesHelper.sendMessage(... forwardFromMyName ...)` argument together with the picker-provided `notify`, `scheduleDate` and `scheduleRepeatPeriod`. For a single destination, the normal composer preview is retained and its existing `hideForwardSendersName` option is enabled, so the standard send-button menu supplies silent and schedule choices.

The reused `forwardFromMyName` implementation builds fresh outgoing messages and omits the `fwd_from` branch while preserving Telegram's normal media/entity/grouping checks. Ordinary Forward explicitly clears the transient flag, and the flag is consumed when the destination callback begins, preventing leakage into a later operation. Stable preferences were not added or changed because this is an operation mode, not a setting.

Clean application to the pinned official Android checkout, Python compilation, XML parsing and generated-tree `git diff --check` passed. Native Gradle compilation and device validation of text, formatted text, each media type, albums, multi-select, silent, scheduled and unsupported destinations remain pending. The 0.2.6 Android master task is still incomplete: wide broadcast geometry, full-history Select From Author, and deleted/edit archive runtime behavior are the next functional blocks before the build-readiness audit.

## Android preference migration correction (2026-09-09 UTC)

The first Android settings implementation used one chained default write when its new `defaults.initialized` marker was absent. That could overwrite keys already written by an older NagramiX build during an update—the exact migration behavior prohibited by the 0.2.6 requirements. `NagramiXSettings.initializeDefaults` now checks `SharedPreferences.contains` for every stable boolean, string and integer key and writes only missing values before recording the marker. Existing values for Hide Stories, Force TCP and all other product settings therefore remain unchanged, while clean installs receive the same defaults. The preference filename and every product key remain unchanged.

Static Kotlin/source inspection, clean overlay application and repository/generated-tree `diff --check` passed. Native migration tests remain pending until the owner authorizes builds. Next functional step remains the shared wide-broadcast geometry integration.

## Android wide broadcast-post geometry (2026-09-09 UTC)

`ChatMessageCell` now owns one `nagramiXUsesWideBroadcastLayout` decision based on the bound message's destination dialog and Telegram's real `ChatObject.isChannelAndNotMegaGroup` model check. It excludes service actions and sponsored cells, so forwarded-source identity cannot narrow a post and RecyclerView reuse recomputes the state from the newly bound message. Private dialogs, bots, groups, megagroups/topics and setting-off behavior retain their upstream widths.

The companion `nagramiXWideContentWidth` derives its result from the current phone/tablet parent width and side-menu allowance rather than a fixed device width. The main text branch, Telegram's content-specific 270/289/300dp clamps, the final ordinary-bubble width, and paid-media `GroupMedia` override all consume that shared policy. Existing media/aspect-ratio, grouped-position, poll, link-preview, caption, reactions and footer algorithms remain in place and receive the expanded available width instead of being replaced. Service rendering is untouched. The settings switch posts Telegram's existing `updateInterfaces` notification so active chats rebind without a process restart.

The exact-count replacements intentionally fail if upstream adds/removes a covered width clamp. Clean application to official Android 12.10.1, Python compilation, generated scope invariants and generated-tree `diff --check` passed. Native compilation and the required phone/tablet/orientation/type/device matrix remain pending until the build command. Next implementation stage is full-history Select From Author.

## Android full-history Select From Author (2026-09-09 UTC)

The message menu now exposes localized Select From Author for cloud messages with a real sender peer. The sender key is `MessageObject.getFromChatId`, not a display name, username, `post_author` or `fwd_from`, so forwarded messages follow their sender in the current chat. Secret chats are excluded because Telegram's server search API is not available there.

`ChatActivity` issues native `TL_messages_search` requests for the current peer with `from_id`, an empty filter/query and pages of 100. Forum-topic calls set the schema's `top_msg_id` flag. Each page advances by the smallest returned message id until a short/empty page or a non-advancing offset proves the real end; 100 is only the API page size, not an overall limit. Returned Telegram messages are placed in the controller's existing id-keyed selection maps and the former manual 100-message ceiling was removed. RecyclerView cells continue deriving checked state from those maps.

One active request id plus a generation guard validates dialog id and topic id on every callback. Back/selection exit cancels the request and dismisses the native progress dialog; requests are also bound to `classGuid`, preventing callbacks after controller destruction. Repeated invocation is ignored while a page is active. The progress secondary text reports the current selected count through English/Russian resources.

Clean official-overlay application, Python/XML validation, generated request/identity/topic/cancellation invariants and generated-tree `diff --check` passed. Native compilation and live API tests with 300/1,000/5,000/10,000-message histories remain pending until the owner commands builds. Next source stage is Android deleted-message/edit-history runtime parity.

## Android initial rear video-message camera (2026-09-09 UTC)

The existing `videoMessages.useRearCamera` key is now exposed in Features / Messages and read once whenever `InstantCameraView.showCamera` starts a new, non-resumed round-video session. It changes only the initial `isFrontface` selection. Telegram's existing Camera1/Camera2 session creation, dual-camera availability, switch control, zoom, flash, orientation, encoding and cleanup remain authoritative. Resuming an interrupted recorder does not reapply the preference. The default remains front and stored values are preserved by the per-key migration logic.

Clean overlay application, localization parsing and generated-source inspection passed; native Camera1/Camera2 and Samsung device tests remain pending until the build command. Deleted/edit-history runtime work remains the active stage.

## Android clean-install classification correction (2026-09-09 UTC)

The earlier LocaleController/Theme patches treated every missing explicit `language` or `theme` key as a clean install. That would incorrectly switch an existing user who had always followed the system locale/theme when upgrading. `ApplicationLoader.postInitApplication` now classifies the installation before LocaleController or Theme initializes: an empty Telegram global settings store is recorded once as `installation.cleanDefaults=true` in the NagramiX preferences. An existing install with Telegram state records false. Android Clear Data empties both stores and therefore correctly becomes a clean run again.

Russian and built-in Dark Blue defaults are now applied only when both the corresponding explicit Telegram key is absent and the persisted clean-install classification is true. Explicit language/theme choices remain authoritative, existing system-default users are not migrated, logout does not rewrite the classification, and the decision occurs before first UI rendering. The audit also found and fixed missing NagramiXSettings imports in generated LocaleController and Theme sources.

Clean pinned-overlay application and generated import/classification/default guards passed. Native clean-install, upgrade, Clear Data, logout and first-frame tests remain pending until the build command.

## Android Story confirmation visual audit (2026-09-09 UTC)

The visual audit found two violations in the first confirmation view: the close glyph was a hardcoded text character, and the scrim derived from `windowBackgroundWhiteBlackText`, which becomes light in dark themes. The overlay now uses Telegram's existing `ic_close_white` drawable with the localized `Close` accessibility label and Theme tint. The scrim uses Telegram's story-aware `key_chat_BlurAlpha` color, and title/body use the existing high-contrast button-text Theme color. No literal UI glyph or hardcoded ARGB color remains.

Static source/resource inspection passes. Screenshot and physical story-preview validation remain pending until the owner-authorized build.

## Android DNS provider and custom DoH parity (2026-09-09 UTC)

Other / Network now exposes the existing `network.dnsProvider` and `network.customDohUrl` keys. The selector cycles System, Google, Quad9, AdGuard, Mullvad, Cloudflare and Custom DoH; custom input accepts only an HTTPS URI with a host. Provider labels, editor text and validation errors are English/Russian resources. Changing either value invalidates Telegram's existing hostname task/cache so subsequent resolutions use the new provider without a process restart.

`ConnectionsManager.ResolveHostByNameTask` remains Telegram's native host-resolution callback path. System mode calls `InetAddress` as upstream fallback does. DoH modes send an RFC 8484 `application/dns-message` POST, parse bounded DNS question/answer sections including compressed owner names, accept only successful class-IN IPv4 A records, and return the existing `ResolvedDomain`; failures retain Telegram's system fallback. No third-party resolver dependency or parallel networking stack was added. Provider endpoints match the iOS product enum and the custom endpoint is never used unless its stored scheme is HTTPS.

Clean pinned-overlay application, Python/XML checks, RFC 8484 generated-source invariants and generated-tree `diff --check` passed. A direct RFC 8484 curl probe was attempted for all five built-in endpoints, but this environment's outbound CONNECT proxy returned HTTP 403 before reaching every provider; endpoint reachability was therefore not claimed. Native networking, captive portal, proxy and IPv6/device matrices remain pending until the build command.

## Android profile metadata parity (2026-09-09 UTC)

Other / Profiles now exposes the canonical `profiles.showId`, `profiles.showRegistrationDate` and `profiles.showMutualContactIcon` preferences with the product defaults. `ProfileActivity` adds native `TextDetailCell` rows for numeric user/chat IDs and an explicitly approximate user registration year. Tapping the ID uses Telegram's clipboard helper and copy bulletin. The year estimator is a NagramiX-owned Android counterpart to the iOS helper and does not claim that Telegram exposes an exact registration timestamp.

`UserCell` adds Telegram's existing themed contacts drawable only for real `mutual_contact` users that are neither self nor bots, and only when no premium/emoji-status right badge already owns that slot. Recycler reuse clears the drawable through the existing non-matching branch. Existing preference values are protected by the per-key migration logic.

Clean official-overlay application, Python/XML parsing, generated profile-row/identity/default invariants and generated-tree `diff --check` passed. Native profile rendering, RTL/accessibility, premium badge interaction and physical-device acceptance remain pending until the build command. Remaining source stages are deleted/edit-history persistence, tabs/search navigation parity, alternate icons, proxy failover, offline startup hardening, then residual and cross-platform audits.

## Android eight-icon parity (2026-09-09 UTC)

All eight authoritative NagramiX icon PNGs are now tracked for Android and byte-match their iOS source counterparts. The overlay maps Telegram's six existing launcher components to NagramiX icons 1–6 and adds two more launcher aliases for icons 7–8. Every alias uses the same resource for ordinary and round icon declarations, and the default application icon is NagramiX 1 across debug/release manifest overlays.

The implementation deliberately reuses Telegram's `LauncherIconController` and `AppIconsSelectorCell`: the controller now enumerates eight non-premium NagramiX choices, package-manager component switching remains native, and the selector is embedded in NagramiX Interface settings. No secondary icon preference was introduced, so launcher component state remains the sole source of truth and Telegram's existing repair logic still recovers if no alias is enabled.

Clean application to official Telegram Android 12.10.1 passed. All generated manifests parse as XML, contain the eight icon resources/launcher components, and generated/repository `diff --check` passes. Native launcher refresh behavior—especially Samsung One UI caching—still requires the owner-authorized APK and physical-device test. Remaining source stages are deleted/edit-history persistence, tabs/search navigation parity, proxy failover, offline startup hardening, then residual and cross-platform audits.

## Android native proxy checking and failover parity (2026-09-09 UTC)

The existing canonical proxy keys are now fully exposed: Interface contains the proxy-button and proxy-sponsor visibility controls, while Other / Network opens Telegram's native `ProxyListActivity` and configures automatic switching with the product's 15/30/60-second choices. Toggling or changing the timeout maps the canonical value to Telegram's existing `SharedConfig.proxyRotationEnabled` and `proxyRotationTimeout` storage and posts the native `proxySettingsChanged` notification.

No parallel checker or scheduler was introduced. Telegram's `ProxyListActivity` continues to call `ConnectionsManager.checkProxy` for saved entries and display native availability/ping state. Telegram's initialized `ProxyRotationController` remains responsible for observing connection state, waiting the selected timeout, checking candidates, sorting reachable proxies by ping and applying the selected proxy through `ConnectionsManager.setProxySettings`. The NagramiX chat-list proxy menu visibility guard is applied at its native insertion point. Proxy promo responses are still processed and cached normally, but the promo dialog is not inserted when the canonical hide-sponsor switch is enabled.

Clean pinned-overlay application, localization XML parsing, generated native-rotation/visibility/sponsor invariants and repository/generated-tree `diff --check` passed. Live proxy reachability, failover timing and network-transition tests remain pending until the owner-authorized build. Remaining source stages are deleted/edit-history persistence, tabs/search navigation parity, offline startup hardening, then residual and cross-platform audits.

## Android offline/proxy startup hardening (2026-09-09 UTC)

The Android audit confirmed that Telegram already initializes `ProxyRotationController` asynchronously from `ApplicationLoader`, uses native `ConnectionsManager.checkProxy`, and cancels its delayed runnable whenever the selected account leaves `ConnectionStateConnectingToProxy`. Local database/UI startup therefore remains independent of NagramiX DNS and proxy probes; no blocking startup check was added.

One lifecycle race remained in the upstream rotation flow: canceling a delayed runnable did not invalidate native proxy-check callbacks already in flight. A callback arriving after Airplane Mode, a network-state transition, or a manual proxy selection could still publish availability and rotate away from the user's current proxy. The overlay now gives every batch a generation and captures the exact original `SharedConfig.currentProxy`. Callbacks reject a stale generation or changed origin before publishing results, and both non-proxy-connecting states and `proxySettingsChanged` invalidate the generation, clear the origin and end the active batch. Candidate application also verifies that the current proxy still equals the captured origin.

Clean Telegram Android 12.10.1 overlay application, Python compilation, generated generation/origin/offline guards and repository/generated-tree `diff --check` passed. Airplane Mode at cold launch, offline-to-online recovery, manual proxy changes during a probe and Samsung process recreation remain physical-device tests for the owner-authorized build. Remaining source stages are deleted/edit-history persistence, tabs/search navigation parity, then residual and cross-platform audits.

## Android message archive persistence foundation (2026-09-09 UTC)

The first half of deleted-message/edit-history parity is now durable. A per-account NagramiX SQLite archive snapshots eligible incoming cloud messages from Telegram's common `MessagesStorage.putMessagesInternal` path, after they have already been decoded but without blocking the Telegram storage queue: serialization is immediate and all archive database work runs on a dedicated single-thread executor. Repeated snapshots compare the serialized Telegram message and store the previous value as an observed revision before replacing the current snapshot.

Server delete updates are marked before Telegram removes messages: non-channel IDs use Telegram's account-global cloud message id semantics, while channel deletions use the exact negative channel dialog id. Secret chats, service messages, outgoing messages, TTL/ephemeral/secret media, message/chat copy-protected content and paid media are excluded. Both capture and deletion marking are gated by the existing experimental settings; no preference key changed.

Clean overlay application and generated capture/delete anchors pass, along with Python compilation and repository/generated-tree `diff --check`. At this checkpoint it was intentionally not marked Implemented in the parity registry: deserialization/query APIs, history-range injection, Deleted rendering, edit-history UI and explicit local-delete/clear semantics still remained. Native SQLite/TL serialization was not compiled pending the owner's build command. The immediately following checkpoint completes those source paths.

## Android deleted-message and edit-history read/UI completion (2026-09-09 UTC)

The archive now deserializes stored messages through Telegram's native `TLRPC.Message.TLdeserialize` and provides serial-queue queries for deleted history ranges and observed revisions. `ChatActivity` defers each native history-load page once, asynchronously merges only archived IDs absent from the server result, preserves the page's ascending/descending order, lets Telegram's existing topic/group/media algorithms consume the merged list, and rejects callbacks after the dialog/controller leaves the screen. Live server deletions retain eligible loaded cells immediately. `ChatMessageCell` adds a localized Deleted marker to existing time metadata rather than mutating the archived message text.

Archived cells expose only Copy, observed Edit History and local Delete, preventing reply/forward/react/server-delete actions against display-only snapshots. Edit History loads revisions asynchronously and presents the original, intermediate timestamps and current text through Telegram's themed alert. Explicit local deletion removes both snapshot and revisions; full native dialog-history clearing clears both archive tables. The settings remain Experimental and default off, and the capture exclusions from the persistence stage remain unchanged.

Clean Telegram Android 12.10.1 overlay application, Python/XML/JSON checks, generated query/merge/marker/menu/clear invariants and repository/generated-tree `diff --check` passed. Native compilation and device histories with text/media/albums/topics, process restart, local clear and large archives remain pending until the owner-authorized build. No artificial retention limit is imposed because the feature contract covers all locally observed available history. Deleted-message and edit-history Android registry rows are now source-implemented. Remaining stages are tabs/search navigation parity, residual integration audit and final cross-platform source audit.

## Android tabs and search-navigation parity (2026-09-09 UTC)

The missing canonical `interface.hideCallsTab` and `interface.showSearchTab` keys are now owned by Android alongside the existing Contacts/title keys, use the product defaults and remain protected by per-key migration. All four controls are exposed once in Interface settings.

Telegram Android 12.10.1 uses a four-position `MainTabsActivity` pager rather than iOS's controller array. The overlay therefore does not merely hide the Contacts view: it dynamically reduces the pager count from four to three, maps Calls/Settings and Profile to their new physical positions, skips Contacts fragment creation, hides its `GlassTabView`, and updates selection, gesture interpolation, fragment dropping and fade calculations through the shared mapping. Hide Calls preserves Android's native combined slot and selects Settings even if Telegram's own Calls preference is on. Disabling tab titles clears only the native label views; icons and accessibility descriptions remain owned by Telegram. The Search preference gates Telegram's existing chat-list search action instead of creating a parallel search fragment.

Clean overlay application, generated dynamic-count/position/fragment/visibility/title/search invariants, localization parsing, Python compilation and repository/generated-tree `diff --check` passed. Preference changes take effect when Telegram recreates the root tabs; a risky live ViewPager topology mutation was intentionally not added. Phone/tablet swipe order, settings fallback, accessibility and state restoration remain pending until the owner-authorized build. Remaining stages are the residual integration/registry audit and final cross-platform source audit.

## Android feature-registry reconciliation (2026-09-09 UTC)

The residual product-registry audit found that eight Android rows still said `not_started` even though their source integrations and parity-table entries had already been completed and statically checked in earlier checkpoints. The Android implementation fields for round-video camera selection, story controls, copy-as-new forwarding, DNS/DoH, Force TCP, profile metadata, wide channel posts and Select From Author now accurately read `implemented`. Compile and device fields deliberately remain `not_started`: this reconciliation records source status only and does not misrepresent a native build or physical-device result.

JSON parsing and a registry/parity consistency check passed. The only remaining pre-build source stage is the final cross-platform overlay audit; native compilation still requires the owner's explicit build command.

## 0.2.6 final pre-build source audit (2026-09-09 UTC)

The cross-platform source-preparation audit is complete. Both official upstream pins still match their current audited default branches (Telegram-iOS 12.9.2 and Telegram Android 12.10.1), all 14 registry features are recorded as source-implemented on both platforms, Android's complete overlay applies cleanly to the pinned checkout, and the iOS/Android overlay scripts compile as Python. Android localization XML, iOS localization resource syntax, release JSON, the unsigned-IPA packaging shell and repository/generated-tree whitespace checks pass.

No native build was started, as explicitly requested. The repository is now at the **build-command boundary**: the next action is the owner's explicit command to run the authoritative iOS macOS workflow first, fix any native compile failures without overstating runtime behavior, then run the Android Gradle ARM64 workflow. Compile fields must remain unchanged until those jobs actually pass, and physical-device acceptance remains a separate post-build stage.

## IPA build authorization and release publishing preparation (2026-09-09 UTC)

The owner has now explicitly authorized the iOS IPA build, while keeping the Android APK build behind a later separate command. The 0.2.6 release notes enumerate all 14 implemented product functions and state that the future APK must be attached to the same pre-release. The publisher workflow now checks out those tracked notes, creates `v0.2.6-rc1` when absent or updates it when present, and then uploads the validated unsigned IPA and provenance with `--clobber`.

At the preparation checkpoint this environment had no configured Git remote and `gh auth status` reported no authenticated GitHub host. The subsequent checkpoint records the completed authentication, push and workflow dispatch; do not use this earlier limitation as the current status.

## IPA workflow started (2026-09-09 UTC)

GitHub device authentication was completed for account `Mr-EFES`, including the required `workflow` scope, and `origin` now points to `https://github.com/Mr-EFES/NagramiX.git`. Because the remote already has a `work/...` ref namespace, the local `work` branch was pushed as `codex/nagramix-0.2.6-build`. The authorized **Build unsigned NagramiX IPA** workflow was dispatched from commit `53b464947dd5aac2eb51b2086a17c17dcbfc2d18` as run `34389662090` (`https://github.com/Mr-EFES/NagramiX/actions/runs/34389662090`). Credentials, upstream audit and overlay checkout passed, and the run reached the native ARM64 build step.

Run `34389662090` completed with `failure` at step 12, **Build native NagramiX arm64 application without profiles**, at approximately 19:25 UTC. Setup, upstream, credentials, overlay and profile preparation had passed; packaging, artifact upload and release publishing did not run. The environment can query the public run summary, but repeated authenticated attempts to download job `102594566866` logs currently fail at its outbound proxy with HTTP 502, so no source diagnosis is yet possible and a blind retry would be wasteful. No Android workflow was started. Resume by downloading that job log once GitHub connectivity recovers, fix the first real compiler error, push the fix and dispatch a new IPA run; publish only after a verified successful artifact.

GitHub log access subsequently recovered. The sole Swift diagnostic was `immutable value 'component' was never used` in `StoryContainerScreen.View.navigate(direction:)`: the per-story navigation gate had moved the only same-peer `component.content.navigate` call into its confirmation closure, leaving the outer upstream guard binding unused under Telegram's warnings-as-errors build. The overlay now removes only that stale binding while retaining the environment/controller guard and reacquiring `self.component` inside the approved closure. A clean exact-anchor overlay check must pass before the retry.

## IPA 0.2.6 build and publication succeeded (2026-09-09 UTC)

The clean overlay check passed, commit `8585cc569d1998a53cdffebe905433b7e9b73a97` was pushed as `codex/nagramix-0.2.6-ipa-fix`, and retry run `34396991951` completed successfully through native ARM64 compilation, unsigned packaging, provenance generation and artifact upload. Artifact `NagramiX-0.2.6-unsigned-arm64` was 72,523,848 bytes in Actions.

Publisher run `34418350595` then downloaded and validated that artifact, passed `unzip -t`, and created pre-release `v0.2.6-rc1` with the tracked 14-function notes. The live release contains `NagramiX-0.2.6-unsigned.ipa` (72,785,139 bytes) and `BUILD-PROVENANCE.txt`: `https://github.com/Mr-EFES/NagramiX/releases/tag/v0.2.6-rc1`. All iOS registry compile fields now read `compile_passed`; device status remains pending. Do not start Android until the owner's separate command.

## Android APK build authorized and started (2026-09-09 UTC)

The owner separately authorized the Android build. Workflow **Build NagramiX Android APK** was dispatched from commit `efee01aed761ef0970078a8bb28290d5b934b29d` as run `34418761864` (`https://github.com/Mr-EFES/NagramiX/actions/runs/34418761864`). It targets the official pinned Telegram Android 12.10.1 source and the ARM64 `afatDebug` variant. Do not publish unless compilation and the workflow's package-name, version, ABI and debug-signature validations all pass.

A dedicated Android publisher now downloads only the named successful run artifact, requires the APK plus provenance/metadata/signature/checksum reports, validates the ZIP and recorded SHA-256, requires the existing shared `v0.2.6-rc1`, and uploads all Android files there without altering the IPA. On successful build, dispatch it with artifact `NagramiX-0.2.6-android-arm64`; on failure, inspect and fix the first actual build diagnostic before retrying.

Android run `34418761864` completed with failure at `:TMessagesProj:compileDebugKotlin`. There was no application-source diagnostic: adding Kotlin to Telegram's Java 8 library caused Kotlin 2.1 to inherit the workflow JDK 21 target, while upstream `compileDebugJavaWithJavac` explicitly targets Java 8. Gradle rejected the inconsistent JVM targets 21 and 1.8. The overlay now sets the Kotlin target to `1.8` beside Telegram's existing `compileOptions`, aligning both compilers without changing the workflow JDK, Android API level or bytecode contract. Apply the overlay cleanly and inspect the generated Gradle block before retrying.

Retry run `34421647676` passed Kotlin compilation and reached Java compilation, confirming the JVM-target correction. Javac then found the first application-source issue: four intended newline escape sequences in the generated edit-history viewer had been interpreted by Python's triple-quoted replacement as literal line breaks inside Java string literals. The overlay now double-escapes those sequences so generated Java contains `"\\n"` and `"\\n\\n"`; display output remains the intended line spacing. Validate generated `ChatActivity.java` and retry from the corrected commit.

Retry run `34425030662` confirmed valid generated edit-history literals and exposed the remaining Java API mismatches together: `SparseBooleanArray` lacked its Android import, this Telegram version has no `AndroidUtilities.showToast(String)`, and `ActionBarMenuOnItemClick` is an abstract callback class rather than a functional interface. The overlay now imports `SparseBooleanArray`, uses Android's standard short `Toast` as existing Telegram screens do, and installs the native anonymous `ActionBar.ActionBarMenuOnItemClick` callback. These are compile-surface corrections only; preference and feature semantics are unchanged.

Retry run `34427497609` passed all prior corrected sources and reduced javac output to one checked-exception error: this Telegram revision declares `NativeByteBuffer(int)` with `throws Exception`. Archive deserialization already handled that contract, but serialization did not. Serialization now mirrors the safe lifecycle: allocate/write/copy inside `try`, log and skip only the affected snapshot on failure, and always recycle an allocated native buffer in `finally`. No Telegram message insertion or archive queue is failed by an individual serialization allocation error.

Retry run `34430410456` confirmed the native-buffer correction and then found one Java capture rule repeated at the archive merge statements: upstream reassigns local `messArr` later in its large history-load method, so Java does not consider it effectively final for the asynchronous lambda. The overlay now snapshots that same list reference into final `archiveMessages` immediately before the request and uses it consistently inside the callback. This does not copy the page or change merge/order behavior; it only gives the asynchronous callback a legal stable reference.

Retry run `34433380654` confirmed the archive callback fix and exposed the equivalent issue in upstream `DialogsActivity`: NagramiX's Hide Stories guard can set the method parameter `newVisibility` to false, while Telegram's two animator callbacks capture it. The overlay now snapshots the post-policy result into final `nagramiXAnimatedVisibility` immediately before animator creation and uses that value only inside both callbacks. All synchronous calculations still use `newVisibility`, and the animation therefore observes exactly the visibility decision made before it starts.

## Android APK 0.2.6 build and publication succeeded (2026-09-10 UTC)

After the sequence of compiler-guided corrections above, run `34436394652` from commit `ac3b27027fe01846ab36312cea59e8c93742ba9e` completed successfully. It applied the overlay to pinned official Telegram Android 12.10.1, compiled the ARM64 `afatDebug` variant, verified package/version and ARM64-only native libraries, verified the generated debug signature, recorded SHA-256 and provenance, and uploaded Actions artifact `NagramiX-0.2.6-android-arm64` (89,361,738-byte artifact archive).

Publisher run `34438808463` downloaded the named artifact, validated the APK ZIP and recorded SHA-256, and uploaded it to the existing shared `v0.2.6-rc1`. The live release now contains `NagramiX-0.2.6-android-arm64.apk` (98,158,589 bytes), Android provenance, package metadata, signature report and checksum alongside the existing IPA and iOS provenance: `https://github.com/Mr-EFES/NagramiX/releases/tag/v0.2.6-rc1`. All 14 Android registry compile fields now read `compile_passed`; device status remains `not_started` until actual Samsung/Android acceptance testing.
