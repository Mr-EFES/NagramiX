# Wide channel posts

## Product behavior

When `interface.wideChannelPosts` is enabled, every post rendered for a
broadcast-channel timeline uses the maximum safe horizontal space,
including posts whose text or media would normally produce a narrower intrinsic
bubble. The post retains the native safe-area, list and bubble edge insets.

The floating share and summarize controls are hidden for those channel posts so
they cannot overlap the expanded bubble. Telegram's native long-press/context
menu actions remain available. Media, text, links, quotes, reactions, view/edit
metadata, comments and grouped posts continue through their native content and
layout nodes; NagramiX changes the outer width constraint and the resulting
bubble width, not the reaction or content implementations.

Channel identity is resolved from `chatLocationPeerId`, rather than from the
individual message's source peer. This includes text, photo/caption, video,
grouped-media, forwarded-content and sponsored entries displayed in that
channel, while avoiding channel-sourced forwards displayed in an unrelated
private chat or group. The option does not affect private chats, groups or
Saved Messages. The default is `false`, and disabling it preserves official
Telegram layout behavior.

## Implementation

- iOS 0.2.5: native Swift integration and Interface checkbox.
- iOS 0.2.8: force the outer bubble to the maximum safe width instead of merely
  offering that width to intrinsically sized content.
- iOS 0.3.1: resolve eligibility from the destination channel timeline and
  remove content-source/preview/ad exclusions that left some channel posts
  narrow.
