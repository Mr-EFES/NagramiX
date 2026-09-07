# Переслать без / Copy as new

## Transfer modes

NagramiX exposes two explicit message-transfer modes:

- `forwardWithSource` uses Telegram's unchanged `.forward` enqueue path and
  preserves normal forward metadata;
- `copyAsNew` extracts supported content and creates `.message` enqueue values.
  It never invokes `.forward`, mutates the source message, rewrites its author,
  or removes forward metadata after sending.

Both actions use Telegram's standard destination picker and pending-message
pipeline. A single quick destination, including Saved Messages, must enter the
same `copyAsNew` commit path as multi-destination selection; it must never fall
through to Telegram's Saved Messages `.forward` shortcut or destination
forward-composer state.

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

Because the server request is produced from `.message`, the resulting message
has the current destination send identity and no forward header. It therefore
uses Telegram's standard Edit action wherever Telegram normally allows editing
an ordinary outgoing message; NagramiX does not add a custom editor.

## Required device acceptance

The release is not verified until channel, group, private-chat and bot messages
can be copied to Saved Messages without a forward header, retain entities/media,
and ordinary copied text can subsequently be edited with Telegram's native
long-press **Edit** action. Multi-select order and album grouping must also be
verified on a physical device.
