# NagramiX 0.2.4 Android / iOS functional parity

NagramiX is one independent product with native clients based on official Telegram sources. iOS is primary and uses Telegram-iOS 12.9.2. Android is secondary and uses official Telegram Android 12.9.2. NagramX 1258 is an idea reference only.

Status meanings:

- **Implemented:** durable platform-native integration exists in the tracked overlay.
- **Not ported:** no equivalent Android integration exists yet.
- **Pending device:** implemented in source but not tested on a physical device.
- **Verified:** tested on the relevant physical device.

| Capability | iOS 0.2.4 | Android official-base status | Device validation |
| --- | --- | --- | --- |
| Independent branding/package | Implemented | Implemented in Android overlay | Pending device |
| NagramiX settings ownership | Implemented | Kotlin settings namespace added; settings UI not ported | Pending device |
| Hide Contacts tab | Implemented, default on | Not ported | Not tested |
| Hide Calls tab | Implemented, default on | Not ported / Android navigation differs | Not tested |
| Tab titles/search controls | Implemented | Not ported | Not tested |
| Eight NagramiX app icons | Implemented | Primary NagramiX icon only | Pending device |
| Front/rear round video | Implemented | Not ported | Not tested |
| Story controls/confirmation | Implemented | Not ported | Not tested |
| Forward with source | Telegram-native | Telegram-native | Not tested |
| Forward without source/copy-as-new | Implemented | Not ported | Not tested |
| Deleted-message archive | Implemented | Not ported | Not tested |
| Edit history | Implemented | Not ported | Not tested |
| DNS provider/custom DoH | Implemented | Not ported | Not tested |
| Proxy check/failover/button | Implemented | Not ported | Not tested |
| Force TCP calls | Implemented | Not ported as NagramiX user setting | Not tested |
| Profile ID/date/mutual marker | Implemented | Not ported | Not tested |
| Offline/proxy startup hardening | Implemented | Not ported | Not tested |

## Acceptance rule

Matching version numbers or successful compilation do not mean functional parity. Each shared feature requires an Android Kotlin/Java implementation against official Telegram Android, review of platform-specific semantics, and physical-device testing. NagramX code must not be copied or compiled as the implementation shortcut.
