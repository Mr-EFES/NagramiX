# Значок взаимного контакта

Существующий ключ `nagramix.profiles.showMutualContactIcon` управляет меткой без дополнительных настроек. Общая native cell `ContactsPeerItem`, используемая главным списком контактов, поиском и recipient/forward picker, проверяет уже загруженный `TelegramUser.flags.contains(.mutualContact)` за O(1). Метка исключает self, bots и пользователей без имени; для device contacts, groups и channels она не создаётся.

Рядом с рассчитанным attributed title добавляется один template-vector `NagramiXMutualContact`, окрашенный `theme.list.itemAccentColor`. Он участвует в штатном title layout рядом с verified/Premium/emoji-status элементами, не меняет высоту строки и не резервирует место при выключенной настройке или non-mutual peer. Title строится заново при каждом bind, что сбрасывает badge при reuse.

Device acceptance обязателен отдельно для Contact List, Forward/recipient picker, ON/OFF, Light/Dark/Black/custom themes и быстрого скролла mutual/non-mutual строк.
