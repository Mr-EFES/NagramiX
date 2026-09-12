# NagramiX bootstrap

NagramiX is an overlay repository for an iPhone client based on pinned official Telegram-iOS source. The complete upstream tree is not stored here.

## Preparation

1. Verify the pin with `python3 scripts/check_upstreams.py --platform ios --require-current`.
2. Check out `TELEGRAM_IOS_REF` from `ios/upstream.env` into a disposable directory.
3. Apply `python3 ios/apply_overlay.py --source <checkout> --configuration <temporary configuration.json>`.
4. Review generated changes and run static checks.

Do not commit upstream checkouts, configurations, profiles, build outputs or signing material.

## Authoritative build

`.github/workflows/build-unsigned-ipa.yml` runs on macOS, applies the overlay, compiles ARM64 and packages an unsigned IPA. `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` remain GitHub Secrets. Physical-iPhone testing is separate from compilation.
