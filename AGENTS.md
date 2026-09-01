# NagramiX Agent Instructions

> **BEFORE MAKING ANY CODE CHANGES, READ THIS FILE AND `docs/AI_HANDOFF.md`.**

## Project identity

- **Name:** NagramiX.
- **Purpose:** an independent, unofficial, modified Telegram client for iOS and Android.
- **Bases:** audited pins of the current official Telegram-iOS and official Telegram Android default branches. At the 2026-09-01 audit these report iOS 12.9.2 and Android 12.10.1. NagramiX is an overlay repository, not a full fork containing either complete upstream source tree.
- **Product priority:** iPhone/iOS is the primary platform. Android is a first-class secondary build for Samsung/Android device testing.
- **Reference project:** NagramX 1258 is used only as a source of product ideas and behavior references. NagramX code is not the Android base and must not be compiled into NagramiX.
- **Platform implementations:** shared NagramiX product behavior is implemented natively in Swift/Objective-C for iOS and Kotlin/Java for Android against the respective official Telegram codebase.
- **Primary technologies:** Swift, Objective-C/Objective-C++, Kotlin, Java, Python, Bash, Bazel/Starlark, Gradle, Xcode and GitHub Actions.
- **Targets:** unsigned ARM64 IPA for physical iPhone installation after external signing (for example with SideStore), and an ARM64 debug-signed APK for physical Android pre-release testing.

### Key directories

- `product/` — the platform-neutral source of truth for NagramiX identity, feature specifications, canonical settings, terminology, parity and release scope.
- `ios/` — the authoritative NagramiX overlay, branding, custom sources, configuration template and patch scripts.
- `android/` — the authoritative Android pin, exact-anchor overlay script and Android-specific documentation.
- `ios/Sources/NagramiXCore/` — persistent settings and NagramiX localization resources.
- `ios/Sources/SettingsUI/` — NagramiX settings, custom DoH UI and the proxy-screen overlay block.
- `ios/Sources/TelegramCore/` — proxy failover controller integrated into TelegramCore.
- `ios/Sources/MtProtoKit/` — custom DNS/DoH resolver integrated into the pinned MtProtoKit sources.
- `ios/branding/` — primary and alternate application icon sources.
- `ios/apply_overlay.py` — top-level overlay entry point used by CI; generates private build configuration, applies branding and invokes the feature patcher.
- `ios/apply_features.py` — exact-anchor patches against the pinned Telegram-iOS revision. Treat this as a high-risk integration file.
- `scripts/package_unsigned_ipa.sh` — strips temporary signatures/profiles, validates metadata and packages the unsigned IPA.
- `.github/workflows/build-unsigned-ipa.yml` — authoritative macOS/Xcode/Bazel build pipeline.
- `.github/workflows/build-android-apk.yml` — authoritative Ubuntu/Gradle Android ARM64 test-APK pipeline.
- `docs/` — bootstrap/release documentation and the current AI handoff.
- `work/`, `.codex-validation-*`, `.codex-tmp-*`, `artifacts/` and `outputs/` — local checkouts, validation copies or build outputs. They are not authoritative source code and must not be edited as a substitute for changing the tracked overlay.

## Repository model

GitHub Actions checks out the pinned Telegram-iOS commit from `ios/upstream.env`, verifies the expected upstream version, then applies the tracked NagramiX overlay to that clean checkout.

Before either platform build, `scripts/check_upstreams.py --require-current` compares the audited pin and version with the official Telegram default branch. A stale result blocks the build until a deliberate upstream migration audits the exact anchors. Never silently build a moving branch or blindly update a pin.

Do not make product changes directly inside a temporary Telegram-iOS checkout and assume they are preserved. Every durable NagramiX change must exist in tracked overlay source, a tracked patch operation, build configuration, documentation or Git history.

The exact string anchors in `ios/apply_features.py` intentionally fail when the pinned upstream source no longer matches. Do not weaken those checks or replace them with best-effort patching without a deliberate upstream migration review.

## Working rules

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
