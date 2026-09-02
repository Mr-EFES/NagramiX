# Product identity

**NagramiX** is an independent, unofficial, non-commercial Telegram client for iPhone and Android. It is not affiliated with, sponsored by or endorsed by Telegram Messenger Inc.

NagramiX is a standalone product with its own features, settings and branding. Its build bases are only audited pins of the official Telegram sources for each platform.

## Platform model

| Platform | Priority | Official source base | Native implementation | Artifact |
| --- | --- | --- | --- | --- |
| iOS / iPhone | Primary | `TelegramMessenger/Telegram-iOS` | Swift, Objective-C/Objective-C++ | unsigned ARM64 IPA |
| Android / Samsung | Secondary, without permanent feature reduction | `DrKLO/Telegram` | Kotlin, Java | debug-signed ARM64 APK |

Shared observable behavior is specified under `product/` and then implemented independently under `ios/` and `android/`. Platform-native UI and lifecycle details may differ, but Android must converge on the same NagramiX product capabilities rather than remain a reduced edition.

NagramiX does not claim ownership of Telegram, the Telegram name, protocol or official source code. Official Telegram code remains governed by its upstream licenses. NagramiX-specific work remains separately identifiable in this overlay repository.

## Platform priority

- **Primary:** iPhone/iOS, implemented with Swift and Objective-C/Objective-C++ against official Telegram-iOS.
- **Secondary first-class platform:** Android/Samsung, implemented with Kotlin and Java against official Telegram Android.

Priority defines development order, not permission for permanent functional degradation. Shared approved functionality targets both platforms.

## Product workflow

1. Capture an idea from the owner, device feedback or another client.
2. Specify behavior, defaults, privacy constraints and acceptance criteria here.
3. Implement iOS natively and validate compilation/device behavior.
4. Port equivalent behavior to Android natively and validate compilation/device behavior.
5. Record intentional platform differences.
6. Include only the actually verified scope in a pre-release.

## Releases

Development artifacts are published as GitHub **pre-releases**. A pre-release may contain both:

- an unsigned ARM64 IPA requiring external signing;
- a debug-signed ARM64 APK intended for physical Android development testing.

Release notes must list upstream versions, minimum OS versions, hashes, signing state, implemented features, pending device tests and known limitations.
