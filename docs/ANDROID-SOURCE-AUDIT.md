# Android source-parity audit

## Scope and result

The tracked Android overlay was compared with the NagramiX 0.2.5 registry and
official Telegram Android 12.10.1 at
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. Every registry row now has a
native Android integration. This is **source parity**, not compiled or
physical-device parity.

## Completed integration review

- Deleted/edit archives restrict capture to eligible incoming cloud messages,
  preserve Telegram's serialized entities/media references, mark observed
  deletions immediately, merge archived deletions after reload, expose revision
  history and clear account-owned data on logout.
- Proxy behavior reuses Telegram Android's native asynchronous `checkProxy` and
  `ProxyRotationController`. Canonical NagramiX preferences synchronize the
  enabled state and 5/10/15/30/60-second timeout; waiting-for-network cancels
  pending rotation through Telegram's existing connection-state observer.
- The proxy entry can remain visible while disabled, and proxy-sponsored promo
  dialogs are discarded when the canonical hide setting is enabled.
- System DNS uses Android `InetAddress` on Telegram's background resolver task.
  DoH validation uses a lifecycle-invalidated dedicated executor.
- Wide posts remain restricted to ordinary broadcast-channel timelines.

## Build boundary

The parity gate passes and the ARM64 debug APK workflow is restored with
`workflow_dispatch` as its only trigger. It validates the current pin, secrets,
ARM64-only libraries, package/version, debug signature, SHA-256 and provenance.
The workflow has **not** been dispatched. Native Gradle/NDK compilation, APK
metadata and all physical-device behavior remain unverified.

## Exact next step

Wait for explicit product-owner authorization to run **Build NagramiX Android
APK**. After the build, inspect all generated evidence before installing on a
physical ARM64 Samsung/Android device.
