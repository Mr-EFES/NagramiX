# Android source-parity audit

## Scope and result

The Android overlay was re-audited for NagramiX 0.2.5 against official
Telegram Android 12.10.1 at `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`.
All release-registry features have durable native Android integrations and the
source-parity gate passes. This is source parity only: Android compilation and
physical-device parity remain unverified until the owner authorizes the manual
ARM64 build and live test.

## Review closure

- Deleted-message reload merges are bounded to the positive-ID range of the
  currently loaded history page, sorted newest first and capped at 100 rows.
- Archive schema version 2 persists forum-topic thread ids; reload uses the
  active `threadMessageId`, preventing cross-topic injection.
- Dialog-scoped and Telegram global deletion events both mark stored rows.
- A deleted archived message exposes only local Copy, observed Edit History and
  local Delete actions; Reply, Pin, Forward, Report and other server actions are
  never inserted.
- Story confirmation is enforced in the shared `StoryViewer.open` entry path,
  covering dialog strips, profiles, chat headers and other native callers.
- Copy-as-new uses one shared support predicate for both menu visibility and the
  defensive send path.
- DNS provider changes invalidate completed cache entries and generation-tag
  in-flight work so obsolete results cannot repopulate the cache.

## Validation boundary

The exact-anchor overlay applies successfully to a clean checkout of the
pinned official source, generated changes pass whitespace checks, and the 0.2.5
registry gate passes. The ARM64 workflow is `workflow_dispatch` only and has not
been dispatched. No Gradle task ran and no APK was created in this audit.
