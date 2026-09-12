# Wide channel posts

## Product behavior

When `interface.wideChannelPosts` is enabled, ordinary posts shown in the main
timeline of a broadcast channel may use the horizontal space that Telegram
normally reserves beside the bubble for its floating share/summarize control.
The post bubble retains the native safe-area, list and bubble edge insets.

The floating share and summarize controls are hidden for those channel posts so
they cannot overlap the expanded bubble. Telegram's native long-press/context
menu actions remain available. Media, text, links, quotes, reactions, view/edit
metadata, comments and grouped posts continue through their native content and
layout nodes; NagramiX changes only the outer width allowance.

The option applies only to the main `.peer` timeline of a broadcast channel. It
does not affect private chats, groups, Saved Messages, replies/comments,
message previews, search results, ads or custom chat contents. The default is
`false`, and disabling it preserves official Telegram layout behavior.

## Implementation

- iOS 0.2.5: native Swift integration and Interface checkbox.
