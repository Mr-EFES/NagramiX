# Select From Author

## Product behavior

The message context action resolves the selected message's real `author.id` and searches the current peer and optional reply-thread through TelegramEngine's native `searchMessages` API. Results are requested repeatedly with the returned `SearchMessagesState` until `SearchMessagesResult.completed` is true, then the accumulated message ids become the chat selection state.

The operation owns a `MetaDisposable`, rejects a second concurrent request, exposes Telegram's cancellable loading overlay, and validates its generation plus peer/thread identity in every callback. Leaving the controller disposes the request. Forward metadata and display names are not used as sender identity.

## Verification

Clean-overlay application and generated-source invariants pass. Native compilation and large-history physical-device tests remain pending.
