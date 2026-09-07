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
[`profile-info.md`](profile-info.md) and [`dns-doh.md`](dns-doh.md).
