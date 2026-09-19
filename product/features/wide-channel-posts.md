# Wide channel posts

## Product behavior

When `interface.wideChannelPosts` is enabled, every ordinary post shown in the
main timeline of a broadcast channel uses the maximum safe horizontal space,
including posts whose text or media would normally produce a narrower intrinsic
bubble. The post retains the native safe-area, list and bubble edge insets.

The floating share and summarize controls are hidden for those channel posts so
they cannot overlap the expanded bubble. Telegram's native long-press/context
menu actions remain available. Media, text, links, quotes, reactions, view/edit
metadata, comments and grouped posts continue through their native content and
layout nodes; NagramiX changes the outer width constraint and the resulting
bubble width, not the reaction or content implementations.

The option applies only to the main `.peer` timeline of a broadcast channel. It
does not affect private chats, groups, Saved Messages, replies/comments,
message previews, search results, ads or custom chat contents. The default is
`false`, and disabling it preserves official Telegram layout behavior.

## Implementation

- iOS 0.2.5: native Swift integration and Interface checkbox.
- iOS 0.2.8: force the outer bubble to the maximum safe width instead of merely
  offering that width to intrinsically sized content.
- iOS 0.3.5: use the pre-intrinsic-clamp safe content width for the final outer
  bubble. The previous finalizer reused `maximumNodeWidth`, which Telegram had
  already reduced to the narrowest content node and therefore left portrait
  media and short posts narrow.
