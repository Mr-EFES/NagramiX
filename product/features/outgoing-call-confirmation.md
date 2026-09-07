# Outgoing call confirmation

When `calls.confirmOutgoing` is enabled, NagramiX asks for explicit confirmation
immediately before an eligible one-to-one outgoing audio or video call enters
the native permission and call-initiation path. Cancelling performs no call-side
effect. Confirming resumes that exact native path once and does not ask again.

The confirmation is not shown for incoming calls or group voice chats. Native
frozen-account, privacy and offline checks remain authoritative and run before
the confirmation. The setting defaults to enabled on both platforms.
