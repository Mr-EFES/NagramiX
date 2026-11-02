# Контакты: молчаливый отказ при запуске

Текущий результат: включено в Release0.6.8/build114; Apple SDK compile и опубликованный IPA проверены. Физическая приёмка **device_pending**. Source-only описания ниже — история подготовки; [актуальный статус](RELEASE_STATUS.md).


21 октября пользователь уточнил контракт: стартовое окно доступа к контактам не показывать; приложение должно продолжать штатную работу, как после «Не разрешать». Контакты Telegram и чаты доступны, а доступ к телефонной книге выдаётся только явным действием пользователя. Прежний обход отменён в итоговом native overlay. Исправление **source_checked / native_compile_pending / device_pending**, в опубликованный IPA113 не входит. Только main, новая сборка не запускалась.

## Что было неверно

Ранний `apply_deferred_contact_permission` лишь исключал контакты из списка стартовых разрешений. Системный статус оставался `.notDetermined`, а `DeviceContactDataManager` игнорировал его и не завершал инициализацию. Исправление113 выдавало отдельный пустой snapshot только потоку отображения номеров: чаты могли открыться, но настоящий importable-поток всё ещё ждал решения. Это не эквивалент штатного отказа.

## Итоговый путь

- `ApplicationContext` записывает штатное подтверждение предупреждения: `ApplicationSpecificNotice.setPermissionWarning(... .contacts, value: 0)`. Оно больше не остаётся «не отвечено». Стартовый выбор не ставит `.contacts` в очередь показа. Восстановлен оригинальный `config.order`, остальные разрешения обрабатываются прежними ветвями.
- Менеджер телефонной книги принимает `.notDetermined` в ту же существующую ветвь отсутствующих данных, что `.denied`: `accessInitialized=true`, `updateAll([:])`. Нативные subscribers получают пустую телефонную книгу; `CNContactStore` не запрашивается и data context не создаётся. Восстановлена оригинальная привязка account.importableContacts и deviceContactPhoneNumbers: отдельный display seed113 удалён.
- Статус разрешения iOS и `DeviceAccess.contactsPromise` **не подменяются**. Нельзя программно поставить системное «Запрещено», не показав системный запрос. Отказ реализован в стартовом сценарии приложения; исходный `.notDetermined` остаётся доступен штатной кнопке явного разрешения. Иначе сохранённый false в общем cache заблокировал бы последующий запрос.
- Нативные кнопки доступа/приглашения/работы с телефонной книгой по явному действию сохраняют реальный `DeviceAccess.authorizeAccess`: если доступ ещё не запрашивался — системный запрос; если iOS уже отказала — штатный переход к настройкам. Реальный последующий grant обновляет менеджер и импорт. Уже выданные права не отзываются.
- `ContactsSettings.synchronizeContacts`, его default true и сохранённые ON/OFF не переписываются. Без системного доступа реальных номеров для импорта нет. После grant сохранённый OFF остаётся OFF. Серверные контакты, их CRUD, предупреждения иных разрешений, контакты-вкладка и её видимость не менялись.

## Интеграция

Финальная `ios/contacts_default_denial.py` / `contacts_default_denial_patches.json` идёт **после transfer_routing**. Два полных SHA256 и пять точных операций проверяются до записи. Ранние исторические стадии оставлены для совместимости цепочки SHA; их фильтрация order и display seed отменяются в конечных исходниках. Нет новых настроек, зависимостей или форматов данных.

У `DeviceContactDataManager` проверен Git blob SHA `864f8588966fc9e7a4305ddc2ba1200cafe33d7c` закреплённого Telegram-iOS13.0/f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838. Остальные paths проверены полным feature overlay.

## Проверка

`scripts/validate_contacts_default_denial.py`:

- **184 проверки** в debug и optimized, warnings-as-errors. Реальные 11 файлов SwiftSignalKit с проверенными Git blob SHA: Promise, Bag, then, mapToSignal и 26-входовый history combineLatest.
- Выполняются извлечённые native callback менеджера, updateAll, importable subscription, оригинальный import preference selector и восстановленные привязки. Воспроизведён прежний случай: display seed готов, importable остаётся pending. Новый `.notDetermined` даёт штатные пустые данные до/после подписки, при absent/ON/OFF sync, без создания phone-book context.
- Нативная обработка статуса и явного запроса DeviceAccess извлечена без изменения. Проверено отсутствие false в cache после молчаливого отказа, последующий explicit grant/denial, существующее разрешение, два аккаунта/отписки, позднее обновление телефонной книги и сохранённый sync OFF. OS/CNContactStore, UI, планировщик и preference values — управляемые границы теста; это не реальные iOS диалоги или доставка контактов на сервер.
- Стартовое предупреждение acknowledged=0 при absent/0/старом значении; modal/default и перестановки server experiment не вызывают запрос контактов. Запрос уведомлений остаётся в очереди.
- Полный overlay **422 файла**, изменились ApplicationContext и DeviceContactDataManager, **420 побайтно прежние**, включая все предыдущие исправления пересылки/рассылки. Дополнительный файл относительно прежнего fixture — проверенный upstream manager, не новый runtime helper.
- **6 отказов без частичной записи**: повторное наложение, missing/drift каждого входа, последняя несовпавшая точка. Swift grammar обоих native файлов, Python AST, metadata/diff.

Proof: `/workspace/.codex-validation-nagramix-contacts-denial/verification.json`, `before.json`, `validation.log`, `overlay-checked.log`; full fixture `/workspace/.codex-validation-nagramix-prefer-ipv6/native-contacts-default-denial-checked`. Apple SDK/IPA и физическое устройство в этой задаче не запускались.

После отдельной команды на IPA: обновить без удаления рабочих данных; проверить запуск, чаты/группы/темы и существующие контакты Telegram без предварительного открытия вкладки Контакты; редактирование облачного контакта и действия, требующие записи в телефонную книгу; явное разрешение/отказ, синхронизацию, сохранённый OFF, повторный запуск и смену аккаунта. Проверить iPhone пользователя и iOS15+; UIKit/cloud CRUD на устройстве пока не подтверждены.
