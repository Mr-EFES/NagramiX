# Android source-parity audit

## Scope

This audit compares the tracked Android overlay with the NagramiX 0.2.5
feature registry and the pinned official Telegram Android 12.10.1 source. It
records source integration only; compilation and physical-device evidence are
tracked separately.

## Source-complete rows

The tracked overlay has native Android integration for settings ownership,
tabs, launcher icons, round-video initial camera selection, story controls,
copy-as-new, DNS/DoH, outgoing-call confirmation, Force TCP, profile metadata
and wide broadcast-channel posts. The wide-post implementation is limited to
ordinary broadcast-channel timelines, disables the floating share and
summarize controls, and expands the existing message width allowance by the
space reserved for those controls. It excludes replies, threads, pinned and
search presentations, sponsored messages, previews and megagroups.

## Remaining source blockers

Android source parity is **not complete**. APK workflows must remain disabled
until all of these blockers are resolved:

1. `deleted_messages` and `edit_history` remain in progress. Their storage,
   deletion capture, merge and viewer paths need a focused lifecycle,
   exclusion and account-cleanup review before being promoted to Implemented.
2. `proxy_failover` is not ported. The existing Android settings are not a
   connectivity controller and must not be counted as implementation.
3. `offline_startup` is not ported. Android needs an evidence-based audit of
   startup and unavailable-proxy behavior before deciding whether a platform
   patch is required.

## Verification performed

- The overlay applies cleanly to official Telegram Android commit
  `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`.
- Exact anchors for the wide-post integration match once.
- PR #9 review corrections cover native System DNS, lifecycle-safe dedicated
  custom-DoH validation, canonical positive chat IDs and launcher-sized assets.
- Python compilation and repository/generated-tree whitespace validation pass.
- Native Gradle/NDK compilation and physical-device behavior are not verified
  by this audit.

## Next step

Finish the archive review, implement proxy failover, audit offline startup,
then rerun the parity gate. Only after it passes should the ARM64 APK workflow
be restored and executed.
