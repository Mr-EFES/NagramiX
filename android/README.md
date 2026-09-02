# NagramiX for Android

Android is the secondary platform of the independent NagramiX application. iOS remains the product priority. Both clients use official Telegram sources as their base and implement shared NagramiX behavior with platform-native code.

## Base and output

- Upstream: official [`DrKLO/Telegram`](https://github.com/DrKLO/Telegram), pinned to Android 12.10.1 and the exact commit in `android/upstream.env`.
- Version: `0.2.4`.
- Package id: `com.mr_efes.nagramix`.
- CI output: an installable ARM64 debug-signed APK for physical-device development testing.

The generated debug signature is not a production identity. Updating over a build signed with another key may require uninstalling the earlier application first.

## Overlay model

`android/apply_overlay.py` verifies the exact official Telegram Android commit, applies independent NagramiX branding/package metadata, injects NagramiX-owned Kotlin settings sources and configures the official build for an ARM64 development APK. The complete upstream Android tree is deliberately not vendored.

Feature work must be expressed as Kotlin/Java sources under `android/Sources/` plus exact integration operations in `android/apply_overlay.py`. A source-name check is not a feature port.

## Current implementation status

This architecture correction establishes the official Telegram base, independent branding, private API credentials, Kotlin compilation and NagramiX settings ownership. It does **not** claim that all iOS NagramiX features are already ported. `docs/ANDROID-FUNCTION-PARITY.md` is the authoritative implementation and device-validation backlog.

## Physical-device focus

After CI produces the replacement APK, test installation, login, messaging, notifications and background recovery first. Feature rows can move to Implemented only after their Kotlin/Java integration exists, and to Verified only after physical-device testing.
