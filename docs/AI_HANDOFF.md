# Текущий контекст NagramiX 0.4.2

Обновлено: 2026-10-04 (Москва). Единственная ветка — main, upstream origin/main.

## Задача и статус

Пользователь сообщил, что в предыдущем IPA все функции работают, кроме оформления. Требует штатные темы Telegram, русский язык при холодном запуске/работе до ручной смены и немедленную сборку 0.4.2 с обычным релизом. Сборка разрешена: publish_release=true, prerelease=false. [Обычный релиз Latest](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.4.2) опубликован, нативная сборка 67 успешна; [статус](PENDING_RELEASE.md), [аннотация](../product/releases/0.4.2.md), [план](IPHONE_TEST_0.4.2.md). iPhone 17 Pro Max, iOS 27.0, SideStore указаны пользователем.

## Реальные изменения

- ios/Sources/SettingsUI/NagramiXSettingsController.swift: удалена дополнительная withModalBlocksBackground; экран использует непосредственно shared presentationData как источник цветов/шрифтов/кнопок.
- ios/apply_features.py: удалено изменение defaultPresentationData по UIScreen; функция совпадает с base Telegram. AppDelegate определяет системное оформление по window.traitCollection, не через ещё отсутствующий rootViewController. Штатные theme factories, palette, theme settings и ручные режимы не модифицированы. Default остаётся dayClassic/system/night. Сохранённые ручные настройки не сбрасываются; старый автоматический выбор Tinted не отличим от ручного.
- Network.swift: langPackCode fallback ru только при languageCode == nil. Сохранённый ручной язык применяется штатно. Интерфейсный defaultPresentationStrings и офлайн официальный RU ресурс уже русские; автоматические предложения иного языка подавлены.
- ios/apply_overlay.py: development region только главного app plist — ru. package_unsigned_ipa.sh проверяет этот ключ. Это не принудительная смена языка системной клавиатуры/всех системных диалогов iOS.

## Проверки

Overlay применён к pin Telegram-iOS 12.9.2 6ad963e5b62d354da79040f388ae2b9132fb17b8. Upstream актуален. Синтаксис изменённых Swift проверен tree-sitter; Python syntax/Shell syntax и метаданные проверены. С baseline отличаются только четыре feature-файла: SettingsController, PresentationData, AppDelegate, Network. Все остальные generated-файлы совпадают побайтно. Восемь файлов stock-тем и defaultPresentationData совпадают с upstream. Нативная компиляция текущей версии прошла в сборке 67; device-проверка новых изменений отсутствует. Подтверждение пользователя относится к предыдущему IPA, не является индивидуальным подтверждением каждого edge case.

## Сохранённые функции и ограничения

Прокси: единое окно 15/30/60 для connecting/updating; резерв только с актуальным native-пингом maxAge180; нет непроверенных probes. Общий checker: два probe по12сек, интервалы120/30, остановка в фоне. Ручная смена отменяет старые поколения/транзакции. Прокси-код этой задачи не менялся. iOS suspend не гарантирует секундные таймеры в фоне; host-статус не различает порты.

Кружки: opt-in отмена прерванного видео-касания вместо delayed lock, dismiss инвалидирует pending запрос. После первого prompt нужен новый hold; намеренный lock вверх сохранён. Камера/жесты этой задачи не менялись.

Архив: локальные копирование/цитата/редактор/copy-as-new/выбор/автор/удаление, метка с корзинкой. Серверное закрепление, редактирование удалённого оригинала, реакции и исходная атрибуция не восстановлены. Медиа требуют доступного cached resource. Поиск: согласованные края, поле48/radius24, item71; категории и handlers сохранены.

Защищённые Stories/read gate/swipes, wide posts/мозаики, IDs/дата, вкладки/прокси/спонсор, камера, DNS и остальные функции сохранены. Не переписывать их. DoH fallback/валидация остаются; сетевые проверки Cloud не заменяют устройство.

## Следующий шаг

Установить опубликованный IPA и пройти план новых сценариев темы и русского cold start на iPhone. Нативная сборка и публикация выполнены, скачанный IPA проверен, README/релиз/статусы compile обновлены. GitHub push через обычный git ранее недоступен; использован /tmp/nagramix-publish.py для exact SHA objects и GitHub update_ref force=false. Сборка должна ссылаться на исходный commit, поздний documentation commit не является новым IPA. Аннотации и коммиты — русские.

Текущая нативная сборка: [№67](https://github.com/Mr-EFES/NagramiX/actions/runs/37230513623), исходный SHA `8ca39b000ed98256bca37dcfe9190408720d9aa0`, publish_release=true/prerelease=false. Компиляция и публикация успешны. SHA-256 `3b705d5a49d0cdd97f0b7ca06ba8d355b096d02ce9ff6acb358d8d6a1e805e2a`. Скачанный IPA проверен: версия/build67, ARM64, RU development region/основные и дополнительные русские ресурсы, bundle ID, отсутствие signatures/profiles, provenance/checksum.
