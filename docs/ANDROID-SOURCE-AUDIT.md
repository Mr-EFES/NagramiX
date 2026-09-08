# Android source-parity audit

## Scope and current result

The Android overlay is audited against NagramiX 0.2.5 and official Telegram
Android 12.10.1 at `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`.
Source parity is **not yet complete**; compilation and device parity are also
unverified.

## Completed integrations

Tabs, icons, round-video camera, proxy rotation/visibility, outgoing-call
confirmation, Force TCP, profiles, offline connection-state behavior and wide
broadcast posts have durable native Android integrations.

## Remaining review blockers

- Deleted archives now resolve global deletion events across their stored owning
  dialogs; loaded-window bounds, forum-topic scope and server-action safety
  remain under review.
- Story confirmation must cover the shared viewer entry path.
- Copy-as-new must hide or reject unsupported content before destination choice.
- DNS provider changes must reject in-flight results from the old generation.

The DNS generation invalidation is implemented locally and awaits review. The
affected registry rows remain `in_progress`, so the parity gate fails.

## Build boundary

Android APK build and publication workflows are absent. No APK was built.
Restore a manual-only workflow only after every blocker is fixed, the clean-pin
overlay applies, and the parity gate passes.
