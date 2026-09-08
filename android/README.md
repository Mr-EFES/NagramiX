# NagramiX for Android

Android is the secondary platform of the independent NagramiX application. iOS remains the product priority. Both clients use official Telegram sources as their base and implement shared NagramiX behavior with platform-native code.

## Base and output

- Upstream: official [`DrKLO/Telegram`](https://github.com/DrKLO/Telegram), pinned to Android 12.10.1 and the exact commit in `android/upstream.env`.
- Version: `0.2.5`.
- Package id: `com.mr_efes.nagramix`.
- Future release output: an ARM64 debug-signed APK, only after source parity.

The generated debug signature is not a production identity. Updating over a build signed with another key may require uninstalling the earlier application first.

## Overlay model

`android/apply_overlay.py` verifies the exact official Telegram Android commit, applies independent NagramiX branding/package metadata and injects NagramiX-owned Kotlin/Java sources. The complete upstream Android tree is deliberately not vendored.

Android APK build and publication workflows remain absent until the second
source review is complete and the parity gate passes honestly.

Feature work must be expressed as Kotlin/Java sources under `android/Sources/` plus exact integration operations in `android/apply_overlay.py`. A source-name check is not a feature port.

## Current implementation status

The overlay integrates a NagramiX entry and native settings surface. Several
0.2.5 integrations remain under source review; compilation and device states
are separate. `docs/ANDROID-FUNCTION-PARITY.md` is authoritative.

## Physical-device focus

After the parity gate permits a future APK, test installation, login, messaging, notifications and background recovery first. Feature rows can move to Implemented only after their Kotlin/Java integration exists, and to Verified only after physical-device testing.
