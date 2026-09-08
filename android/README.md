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

The ARM64 APK build workflow is manual-only and guarded by the source-parity
check. Publication remains unavailable until an authorized native build passes.

Feature work must be expressed as Kotlin/Java sources under `android/Sources/` plus exact integration operations in `android/apply_overlay.py`. A source-name check is not a feature port.

## Current implementation status

The overlay integrates a NagramiX entry in Telegram's main settings and a native settings screen backed by the canonical NagramiX preference namespace. Source integrations are complete for the 0.2.5 registry, but compilation and device verification remain separate states. `docs/ANDROID-FUNCTION-PARITY.md` is authoritative.

## Physical-device focus

After the parity gate permits a future APK, test installation, login, messaging, notifications and background recovery first. Feature rows can move to Implemented only after their Kotlin/Java integration exists, and to Verified only after physical-device testing.
