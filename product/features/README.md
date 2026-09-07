# Feature lifecycle

`registry.json` is the concise parity ledger used for planning and release review.

Statuses:

- `specified` — product behavior and acceptance criteria are approved.
- `not_started` — no durable integration exists.
- `in_progress` — implementation exists but is incomplete.
- `implemented` — durable integration exists and static review passed.
- `compile_passed` — authoritative native build passed.
- `device_pending` — compile passed; physical-device behavior is unverified.
- `verified` — required physical-device scenarios passed.
- `not_applicable` — approved platform exception with a reason.

A feature cannot be called cross-platform complete until both platform records are `verified` or an explicit `not_applicable` exception is approved.

Detailed shared contracts live beside the registry, including
[`profile-info.md`](profile-info.md), [`dns-doh.md`](dns-doh.md), and
[`outgoing-call-confirmation.md`](outgoing-call-confirmation.md). The next
release feature [`wide-channel-posts.md`](wide-channel-posts.md) is tracked
separately from the still-active Android 0.2.4 parity registry.
