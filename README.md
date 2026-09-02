# NagramiX

**NagramiX** — независимый, неофициальный и некоммерческий клиент Telegram для iPhone и Android.

NagramiX является самостоятельным продуктом с собственными функциями, настройками и брендингом. Базой служат только актуально проверенные официальные исходники Telegram для каждой платформы. 

## Приоритет и платформы

| Платформа | Приоритет | Официальная база | Нативная реализация | Артефакт |
| --- | --- | --- | --- | --- |
| iOS / iPhone | Основной | `TelegramMessenger/Telegram-iOS` | Swift, Objective-C/Objective-C++ | unsigned ARM64 IPA |
| Android / Samsung | Второй, без постоянного урезания функций | `TelegramMessenger/Telegram-Android ` | Kotlin, Java | debug-signed ARM64 APK |

Общее продуктовое поведение описывается в [`product/`](product/README.md), а затем независимо реализуется в [`ios/`](ios/) и [`android/`](android/). Похожая функция в стороннем клиенте не считается готовым портом.

## Текущая версия: 0.2.4 pre-release

### Реализовано в iOS

- категории настроек «Интерфейс», «Функции» и «Прочее»;
- управление вкладками, названиями и отдельным поиском;
- восемь иконок NagramiX;
- настройки ленты историй, жеста камеры, подтверждения просмотра и репоста;
- выбор начальной камеры круглого видео с сохранением штатного переключения и zoom;
- режимы пересылки с источником и copy-as-new без источника;
- локально наблюдаемые удалённые сообщения и история правок;
- ID, примерная дата регистрации и значок взаимного контакта в профиле;
- system/custom DoH, проверка прокси, автоматический failover и постоянная кнопка прокси;
- Force TCP для звонков;
- защита offline/proxy запуска.

Нативная iOS-компиляция 0.2.4 пройдена. Полная физическая проверка на iPhone остаётся обязательной для runtime-утверждений.

### Статус Android

Android перестроен на официальную базу Telegram. Независимый package id, брендинг, Kotlin settings foundation и официальный build pipeline подготовлены. Предыдущий APK на базе NagramX архитектурно устарел и должен быть заменён официальной Telegram Android сборкой после прохождения нового CI.

Большинство продуктовых функций ещё требуется реализовать нативно на Kotlin/Java. Честный статус каждой функции находится в [`product/features/registry.json`](product/features/registry.json) и [`docs/ANDROID-FUNCTION-PARITY.md`](docs/ANDROID-FUNCTION-PARITY.md).

## Совместимость

### iPhone

- текущий официальный pin: Telegram-iOS 12.9.2;
- минимальная версия: **iOS 13.0**;
- IPA не содержит Apple-подписи и требует внешней подписи, например через SideStore.

### Android

- текущий официальный pin: Telegram Android 12.10.1;
- минимальная версия: **Android 5.0 / API 21**;
- APK предназначен для ARM64 и подписывается изолированным debug-ключом CI;
- при другой подписи старую тестовую сборку может потребоваться удалить.

Подробности: [`product/COMPATIBILITY.md`](product/COMPATIBILITY.md).

## Структура репозитория

```text
product/     единые функции, настройки, терминология, parity и release scope
ios/         overlay и Swift/Objective-C реализации для Telegram-iOS
android/     overlay и Kotlin/Java реализации для Telegram Android
scripts/     общие проверки upstream и упаковка
.github/     IPA/APK/upstream/publish workflows
docs/        bootstrap, handoff и исторические release notes
```

Полные исходники Telegram не копируются в репозиторий. CI получает закреплённый официальный commit и накладывает контролируемый exact-anchor overlay.

## Проверка актуальности официальных баз

```bash
python3 scripts/check_upstreams.py
python3 scripts/check_upstreams.py --require-current
```

Перед IPA/APK build workflow проверяет официальный master соответствующей платформы. Если pin устарел, сборка останавливается до осознанной миграции и аудита patch anchors.

## Pre-release

Тестовые версии публикуются во вкладке [Releases](https://github.com/Mr-EFES/NagramiX/releases) как **pre-release**. В одном выпуске могут находиться IPA и APK, но только если provenance подтверждает официальную базу каждой платформы. Release notes должны указывать upstream-версии, минимальные OS, подпись, SHA-256, проверенный функционал и известные ограничения.

## Правовой статус

NagramiX — независимое неофициальное некоммерческое приложение. Проект не связан с Telegram Messenger Inc., не спонсируется и не одобряется Telegram. Название Telegram, протокол и официальные исходники принадлежат их соответствующим правообладателям и используются на условиях upstream-лицензий. NagramiX не заявляет прав на Telegram и отделяет собственные изменения в overlay-слоях.
