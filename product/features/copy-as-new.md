# Переслать без / Copy as new

## Transfer modes

NagramiX exposes two explicit message-transfer modes:

- `forwardWithSource` uses Telegram's unchanged `.forward` enqueue path and
  preserves normal forward metadata;
- `copyAsNew` extracts supported content and creates `.message` enqueue values.
  It never invokes `.forward`, mutates the source message, rewrites its author,
  or removes forward metadata after sending.

Standard forwarding keeps Telegram's multi-destination picker and unchanged
direct forwarding behavior. Copy-as-new deliberately uses single-destination
selection: choosing a peer opens that real `ChatControllerImpl`, places the
source text or supported media caption in its ordinary editable text input, and
retains the supported source media as a transient controller payload. It does
not enqueue anything from the picker.

The normal forward-id accessory is used only to keep Telegram's standard send
button and native long-press Send Options available. Inside
`ChatControllerNode.sendCurrentMessage`, and only while the transient copy
payload is present, those ids are converted to fresh `.message` values instead
of `.forward` values. The resulting messages then continue through the existing
`sendMessages(messages, silentPosting, scheduleTime, repeatPeriod, postpone)`
pipeline. Normal, silent, scheduled and when-online delivery are therefore
selected and executed by Telegram's existing composer code rather than by a
NagramiX picker callback.

Telegram exposes **Send When Online** only for an eligible offline user in a
private chat. Copy-as-new must preserve that native presence/capability check;
it must not force the option into groups, channels, service chats or private
chats where Telegram itself suppresses it.

Dismissing the forward accessory while a copy-as-new payload is active is a
real cancellation: NagramiX clears the transient source payload and the
text/caption it seeded into the composer. Telegram's ordinary Forward path is
unchanged and continues to preserve an unrelated user-written draft.

## Preserved content

Text and captions retain the original `TextEntitiesMessageAttribute`, including
formatting, links, mentions, code, spoilers and custom emoji. Associated custom
emoji media is passed through the native inline-sticker map. Photos, videos,
animations, documents, audio, voice messages, video messages and stickers use
their existing `TelegramMediaImage` or `TelegramMediaFile` message reference;
contacts and locations use their native media objects. Telegram resolves or
reuses those references through its normal enqueue/upload implementation.

Albums receive a new local grouping key per original group while preserving the
selected message order. Source reply ids, source thread ids and source forward
attributes are never copied. A selected destination topic may supply its own
thread id. Telegram's normal destination send identity, scheduling, silent-send
and paid-message transformations remain authoritative.

## Safety and atomicity

Secret chats, protected/no-forward messages, self-destructing or expired media,
paid content and unsupported media are rejected. A multi-message selection is
accepted only when every item can be recreated; unsupported items are not
silently omitted and partial copies are not sent.

For a single source message, edits made in the composer replace that message's
text or supported media caption before the `.message` value is built. Because
the server request is produced from `.message`, the resulting message
has the current destination send identity and no forward header. It therefore
uses Telegram's standard Edit action wherever Telegram normally allows editing
an ordinary outgoing message; NagramiX does not add a custom editor.

## Required device acceptance

The release is not verified until channel, group, private-chat and bot messages
open in the selected destination composer before sending; editable text and
supported captions retain entities/media; normal, silent, scheduled and
when-online modes use Telegram's native send menu; and the received message has
no forward header or source author. Standard Forward must be regression-tested
separately. Multi-select order and album grouping must also be verified on a
physical device.
