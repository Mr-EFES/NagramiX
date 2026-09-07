# NagramiX 0.2.4 Android / iOS functional parity

NagramiX is one independent product with native clients based on official Telegram sources. iOS is primary and currently uses Telegram-iOS 12.9.2. Android is secondary and currently uses official Telegram Android 12.10.1.

Status meanings:

- **Implemented:** durable platform-native integration exists in the tracked overlay.
- **Not ported:** no equivalent Android integration exists yet.
- **Pending device:** implemented in source but not tested on a physical device.
- **Verified:** tested on the relevant physical device.

| Capability | iOS 0.2.4 | Android official-base status | Device validation |
| --- | --- | --- | --- |
| Independent branding/package | Implemented | Implemented in Android overlay | Pending device |
| NagramiX settings ownership | Implemented | Settings namespace and native settings screen integrated | Pending device |
| Hide Contacts tab | Implemented, default on | Integrated with native main-tab visibility | Pending device |
| Hide Calls tab | Implemented, default on | Integrated; Settings occupies the shared native position | Pending device |
| Tab titles/search controls | Implemented | Tab-title visibility and separate native Search button integrated | Pending device |
| Eight NagramiX app icons | Implemented | Eight Android-owned launcher aliases integrated with the native icon selector | Pending compile/device |
| Front/rear round video | Implemented | Initial camera setting integrated with native recorder paths | Pending device |
| Story controls/confirmation | Implemented | Strip visibility, pre-view confirmation and repost setting integrated; camera-swipe control not applicable to current Android UI | Pending device |
| Forward with source | Telegram-native | Telegram-native | Not tested |
| Forward without source/copy-as-new | Implemented | New-message pipeline for supported text/media, entities, spoilers and albums | Pending device |
| Deleted-message archive | Implemented | Account-local snapshot storage, exclusions and chat merge in progress | Not tested |
| Edit history | Implemented | Observed-revision capture and context-menu viewer in progress | Not tested |
| DNS provider/custom DoH | Implemented | System plus five named RFC 8484 providers and validated custom HTTPS endpoint integrated | Pending compile/device |
| Proxy check/failover/button | Implemented | Not ported | Not tested |
| Outgoing call confirmation | Implemented | Native one-to-one audio/video start path requires confirmation when enabled | Pending compile/device |
| Force TCP calls | Implemented | NagramiX setting integrated with native VoIP endpoints and P2P policy | Pending device |
| Profile ID/date/mutual marker | Implemented | Copyable peer ID, matching approximate-year ranges and real mutual-contact icon integrated | Pending compile/device |
| Offline/proxy startup hardening | Implemented | Not ported | Not tested |

## Acceptance rule

Matching version numbers or successful compilation do not mean functional parity. Each shared feature requires a NagramiX-owned Android Kotlin/Java implementation against official Telegram Android, review of platform-specific semantics, and physical-device testing.

Android APK build and publication workflows are intentionally absent while any
Android implementation row is incomplete. Compilation and device states remain
separate evidence after the source-parity gate passes.
