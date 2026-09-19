# Mutual contact badge

When `profiles.showMutualContactIcon` is enabled, a real user whose Telegram
peer flags contain `.mutualContact` displays a visible localized `👥 Mutual
contact` badge in the profile information section. Supported native contact
rows also append the theme-tinted compact icon.

The badge is not shown for the current account, bots, non-mutual users,
channels or groups. The peer's native Telegram mutual-contact flag is the only
source of truth; NagramiX does not infer mutual status from local address-book
membership.
