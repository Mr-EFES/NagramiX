# NagramiX product layer

This directory is the platform-neutral source of truth for the independent NagramiX product. It defines **what** a feature means before `ios/` and `android/` define **how** that behavior is integrated into official Telegram sources.

## Rules

1. iOS is the implementation priority, but an approved shared feature is not complete until both platform rows are implemented or a documented platform exception is approved.
2. Official Telegram-iOS and official Telegram Android are the only code bases.
3. NagramX and other clients are idea references only. Their code is not compiled or copied as the implementation.
4. Shared setting ids, defaults, semantics, privacy exclusions and acceptance criteria are defined here first.
5. Swift/Objective-C and Kotlin/Java implementations remain platform-native.
6. Compilation proves build compatibility; device validation is tracked separately.

## Contents

- `PRODUCT.md` — identity, priorities, licensing position and release model.
- `UPSTREAM_POLICY.md` — how current official Telegram revisions are checked and pinned.
- `SETTINGS.md` — canonical NagramiX settings contract.
- `COMPATIBILITY.md` — supported OS versions and artifact/signing expectations.
- `features/registry.json` — machine-readable parity and implementation status.
- `features/README.md` — feature lifecycle and status definitions.
- `releases/0.2.4.md` — current pre-release scope and known limits.
- `localization/TERMINOLOGY.md` — canonical English/Russian product terminology.
