# Compatibility and artifacts

## iPhone / iOS

- Official base: Telegram-iOS version and commit in `ios/upstream.env`.
- Current pinned minimum OS: **iOS 13.0**, taken from the pinned official `Telegram/BUILD` deployment target.
- Output: unsigned ARM64 IPA.
- Installation: requires external signing; SideStore is one possible installation method.

## Android

- Official base: Telegram Android version and commit in `android/upstream.env`.
- Current pinned minimum OS: **Android 5.0 / API 21**, taken from the official Gradle `minSdkVersion`.
- Output: ARM64 APK signed with an isolated development/debug certificate.
- Installation: a differently signed earlier build may need to be uninstalled first.

Minimum versions are properties of the audited official pins, not timeless NagramiX promises. Every upstream migration must re-read and update this file if deployment targets change.
