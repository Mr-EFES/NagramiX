# Official Telegram upstream policy

Before preparing an IPA or APK, NagramiX checks the current default branch of the corresponding official Telegram repository:

| Platform | Official repository | Version source | Local pin |
| --- | --- | --- | --- |
| iOS | `TelegramMessenger/Telegram-iOS` | `versions.json` | `ios/upstream.env` |
| Android | `DrKLO/Telegram` | `gradle.properties` | `android/upstream.env` |

`python3 scripts/check_upstreams.py` reports the official head, reported application version and whether the tracked pin is current. `--require-current` fails if a pin is stale.

A current-head check does **not** authorize a blind pin update. When upstream changes, the migration must:

1. inspect official release/version metadata;
2. update the exact commit and expected version together;
3. apply the overlay to a clean checkout;
4. audit every failed or changed exact anchor;
5. compile on the authoritative platform runner;
6. run the relevant physical-device regression matrix;
7. record the migration in `docs/AI_HANDOFF.md` and release notes.

The repository never silently builds an arbitrary moving branch: checked commits remain reproducible even while the current-upstream audit reports when migration is needed.
