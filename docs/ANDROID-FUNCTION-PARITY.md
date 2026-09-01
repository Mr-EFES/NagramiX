# NagramiX 0.2.4 Android / iOS functional parity

This matrix tracks equivalent user-visible behavior. Android is based on NagramX 1258; iOS is based on Telegram-iOS 12.9.2. Implementations are intentionally platform-native.

| Capability | iOS 0.2.4 | Android 0.2.4 baseline | Device validation |
| --- | --- | --- | --- |
| NagramiX settings | Three iOS categories | Native Nagram/NagramX settings sections | Pending |
| Hide Contacts tab | Default on | Default aligned to on | Pending |
| Hide Calls tab | Default on | Android navigation has no equivalent persistent Calls tab | Not applicable |
| Tab titles | Default shown | Default shown | Pending |
| App icons | Eight iOS alternate icons | NagramX Android launcher aliases/icons retained | Pending |
| Front/rear round video | Front default, selectable rear | Front default, Android camera selector retained | Pending |
| Story header and controls | Header shown by default; controls available | Header default aligned to shown; NagramX controls retained | Pending |
| Forward with source | Native Telegram forwarding | Native Telegram forwarding | Pending |
| Forward without source | Copy-as-new without forward metadata | No-quote forward and repeat-as-copy actions enabled | Pending |
| Deleted messages | Default off, local archive | NagramX saved-deleted implementation, default off | Pending |
| Edit history | Default off, local archive | NagramX edit-history implementation, default off | Pending |
| DNS / custom DoH | System plus named/custom DoH | NagramX system/custom DoH resolver | Pending |
| Proxy management | Check all, failover, persistent button | NagramX proxy management and utilities | Pending; exact failover UX differs |
| Force TCP calls | User-facing NagramiX toggle | Telegram Android Force TCP diagnostic setting and VoIP path | Pending; settings placement differs |
| Profile ID/date/mutual marker | Implemented | NagramX profile information features | Pending |
| Offline/proxy startup hardening | Implemented | Android networking lifecycle is independent | Pending stress test |

## Acceptance rule

A row is not marked verified merely because a source anchor exists or Gradle compiles. Runtime rows require an installable APK and testing on a physical Android device. Any behavioral mismatch discovered on-device must be recorded here and fixed in the tracked `android/` overlay rather than a disposable upstream checkout.
