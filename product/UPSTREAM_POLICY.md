# Official Telegram upstream policy

Before preparing an IPA, NagramiX checks the official Telegram-iOS default branch:

| Platform | Official repository | Version source | Local pin |
| --- | --- | --- | --- |
| iOS | `TelegramMessenger/Telegram-iOS` | `versions.json` | `ios/upstream.env` |

`python3 scripts/check_upstreams.py` reports whether the tracked pin is current. `--require-current` fails for a stale pin. Updating the pin requires review of version metadata, every exact overlay anchor, a macOS compile and physical-iPhone regression testing.
