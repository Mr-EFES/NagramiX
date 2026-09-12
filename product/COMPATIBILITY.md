# Compatibility and artifacts

## iPhone / iOS

- Official base: Telegram-iOS version and commit in `ios/upstream.env`.
- Current pinned minimum OS: **iOS 13.0**.
- Output: unsigned ARM64 IPA.
- Installation: requires external signing; SideStore is one possible method.

The minimum version belongs to the audited upstream pin. Every upstream migration must re-check the deployment target.
