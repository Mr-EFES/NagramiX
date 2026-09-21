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

Channel identity is resolved from `firstMessage.id.peerId`, the destination peer
that Telegram includes in every rendered message's peer dictionary. This
includes text, photo/caption, video, grouped-media, forwarded-content and
sponsored entries displayed in that channel, while avoiding channel-sourced
forwards displayed in an unrelated private chat or group. The option does not
affect private chats, groups or Saved Messages. The default is `false`, and
disabling it preserves official Telegram layout behavior.

## Implementation

- iOS 0.2.5: native Swift integration and Interface checkbox.
- iOS 0.2.8: force the outer bubble to the maximum safe width instead of merely
  offering that width to intrinsically sized content.
- iOS 0.3.1: resolve eligibility from the destination channel timeline and
  remove content-source/preview/ad exclusions that left some channel posts
  narrow.
- iOS 0.3.2: use the message destination id rather than relying on the optional
  chat-location peer being present in each message's peer dictionary.
- iOS 0.3.3: expand the mosaic layout budget itself so multi-photo,
  multi-video and mixed photo/video groups do not retain Telegram's compact
  300-point media cap inside an otherwise wide outer bubble.
- iOS 0.3.4: preserve the common width path for text, single photo/video and
  every grouped-media shape, and make those exact generated-source contracts a
  blocking pre-build validation before producing the physical-device candidate.
- iOS 0.3.6: retain the 0.3.4 implementation and change only the final outer
  width for intrinsically narrow single photos and videos. The bubble uses the
  pre-clamp safe content width while Telegram's existing media renderer retains
  its native aspect fitting and blur-background treatment where needed.
- iOS 0.3.7: after intrinsic measurement, force the final outer width only for
  text-only channel posts. The text-node check deliberately leaves single
  photos, single videos, captions and grouped-media geometry on the 0.3.6 path.
