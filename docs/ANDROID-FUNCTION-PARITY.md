# NagramiX 0.2.6 Android / iOS functional parity

NagramiX is one independent product with native clients based on official Telegram sources. iOS is primary and currently uses Telegram-iOS 12.9.2. Android is secondary and currently uses official Telegram Android 12.10.1. NagramX 1258 is an idea reference only.

Status meanings:

- **Implemented:** durable platform-native integration exists in the tracked overlay.
- **Not ported:** no equivalent Android integration exists yet.
- **Pending device:** implemented in source but not tested on a physical device.
- **Verified:** tested on the relevant physical device.

| Capability | iOS 0.2.6 | Android official-base status | Device validation |
| --- | --- | --- | --- |
| Independent branding/package | Implemented | Implemented in Android overlay | Pending device |
| NagramiX settings ownership | Implemented | Kotlin namespace and localized three-category settings UI implemented | Pending device |
| Clean-install Russian language | Implemented | Implemented before LocaleController applies its initial locale | Pending device |
| Clean-install Telegram Dark Blue | Implemented | Implemented in Theme initialization before first UI | Pending device |
| Hide Contacts tab | Implemented, default on | Dynamic native pager mapping implemented | Not tested |
| Hide Calls tab | Implemented, default on | Native Calls/Settings slot resolves to Settings | Not tested |
| Tab titles/search controls | Implemented | Native labels and chat-list search visibility implemented | Not tested |
| Eight NagramiX app icons | Implemented | Eight native launcher aliases and Telegram icon selector implemented | Pending device |
| Front/rear round video | Implemented | Native initial-camera selection implemented; build pending | Not tested |
| Story controls/confirmation | Implemented | Confirmation, hide tray, recording-swipe guard and native repost visibility implemented | Pending device |
| Wide broadcast posts | Implemented | Shared adaptive ChatMessageCell width policy implemented; native build pending | Not tested |
| Forward with source | Telegram-native | Telegram-native | Not tested |
| Forward without source/copy-as-new | Implemented | Source implemented for single and multi-select; native build pending | Not tested |
| Select from author | Implemented | Server from_id pagination, topic scope and cancellation implemented; native build pending | Not tested |
| Deleted-message archive | Implemented | Account-scoped snapshots, range injection and local-only rendering implemented | Not tested |
| Edit history | Implemented | Observed revisions and native context-menu viewer implemented | Not tested |
| DNS provider/custom DoH | Implemented | System + five RFC 8484 providers + validated custom HTTPS endpoint implemented | Not tested |
| Proxy check/failover/button | Implemented | Native proxy checks/rotation plus visibility controls implemented | Not tested |
| Force TCP calls | Implemented | Implemented through official VoIPService TCP endpoint selection | Pending device |
| Profile ID/date/mutual marker | Implemented | Native profile rows and mutual-contact marker implemented | Not tested |
| Offline/proxy startup hardening | Implemented | Native proxy rotation callbacks hardened for offline/manual changes | Not tested |

## Acceptance rule

Matching version numbers or successful compilation do not mean functional parity. Each shared feature requires an Android Kotlin/Java implementation against official Telegram Android, review of platform-specific semantics, and physical-device testing. NagramX code must not be copied or compiled as the implementation shortcut.
