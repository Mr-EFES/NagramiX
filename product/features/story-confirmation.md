# Story viewing confirmation

When `stories.confirmViewing` is enabled, an unseen story owned by another
account must not become readable or be marked viewed before explicit approval.

Every navigation entry point presents the same full-screen confirmation. Its
background uses both a story thumbnail requested with Telegram's `blurred`
media option and a full-screen dark `UIBlurEffect`; the underlying clear story
viewer is not opened until the user presses the confirmation action. Cancelling
does not approve or mark the story as viewed.

Owned stories, already-seen stories and installations with the setting disabled
retain Telegram's standard behavior.
