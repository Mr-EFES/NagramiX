# Графика и тексты первого запуска

Активны только два точных PNG из архива пользователя19октября:

- `NagramiXOnboardingLogo.png` —1024×1024RGBA, одинаковый логотип всех6штатных страниц.
- `NagramiXOnboardingPhone.png` —1371×1148RGBA, телефон на штатной форме ввода номера.

Файлы побайтно совпадают с ZIP; мастеры OriginalWelcomeLogo.png/OriginalPhoneEntry.png и archive-originals.json находятся в `ios/branding/OnboardingMasters/`. Изображения не перекодируются, не обрезаются и не перерисовываются. Размер определяет stock UIImageView/ASImageNode сaspectFit. `scripts/prepare_onboarding_artwork.py` только проверяет и копирует точные оригиналы.

Communication/Free/Personal/Privacy/Nearby PNG остаются в совместимом manifest и не используются UI. Старые masters/provenance сохраняются как история; не заменять ими новые оригиналы. AppResources —единственный владелец PNG в bundle, повторно в application.resources не добавлять.

`copy.json` —наши13RU/13EN строки, используемые обычными native UILabel. Сохраняются штатные фон/размеры/компоновка/авторизация Telegram. [Контракт и проверка](../../../docs/BRANDED_ONBOARDING.md). Сборка не запускалась.
