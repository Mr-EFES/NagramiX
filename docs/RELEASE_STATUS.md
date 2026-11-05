# NagramiX 0.8.6 — исправление падения PiP после сборки170

**Сборка170: native_compile_passed / package_verified; runtime PiP crash confirmed, публикация запрещена. Исправленный кандидат: source_checked / compile_pending / device_pending.**

[Успешная сборка №170](https://github.com/Mr-EFES/NagramiX/actions/runs/41971313591) · [Исходный Actions ZIP](https://github.com/Mr-EFES/NagramiX/actions/runs/41971313591/artifacts/13394808694).

Оба задания Actions успешно завершились 5 ноября 2026 года, 07:05 UTC. Actor/triggering_actor — Mr-EFES. Пройдены все pre-SDK проверки, cold gate, чистая ARM64-компиляция без восстановления кеша и проверка пакета. База Telegram-iOS13.1.2, pin279f89e4d4f63f17227bf877dc3d8990f22ecd58, минимум iOS15.0. Исправления ошибок168/169 проверены в полном SDK; прежние inference diagnostics исчезли после исправления типов/видимости архива.

- IPA `NagramiX-0.8.6-unsigned.ipa`: **88421881 байт**, SHA256 `b358b77b62450460902d19dd881a795df998a9d5a9550127e06af9fa1802f912`.
- Исходник бинарного пакета: `19bbb2b2a7f463315daa1fb4389a9605984206e9`. Последующая документация в main не меняет этот provenance.
- Исходный Actions ZIP: artifact13394808694, **88078096 байт**, SHA256 `fa5e1e8561aa4580178bde7d42f08cac1979dc9f9e13c30f839da2a1cd25949a`. Скачан через GitHub artifact tool без перепаковки, digest API совпал; CRC и ровно три плоских файла проверены локально.
- Локальный валидатор подтвердил checksum/provenance/version/build/source,6 ARM64/iPhoneOS Mach-O, iOS15+,71 каталог по613 ключей настроек/debug,31 мелодию,8 иконок, отсутствие профилей и временных подписей.
- Символы: artifact13394818659 `NagramiX-0.8.6-symbols-arm64`, SHA256 ZIP `1530f9ce03e1e6565e06b689f423ac031a96333d19594ed601aa5d6f42e63788`. UUID dSYM совпал с IPA и обоими crash-отчётами: `A616A3B2-D778-3FD2-87FC-A90312CF9BCF`.

## Новый кандидат вместо аварийной сборки170

API CLI подтверждает Mr-EFES, но uploads.github.com вернул HTTP401. Создан только собственный пустой draft434878552, tag_name=v0.8.6, target_commitish=19bbb2b2a7f463315daa1fb4389a9605984206e9; файлов в нём нет. Публичного релиза0.8.6 пока нет. Начат официальный device flow владельца, без запроса токенов в чат. После двух crash-отчётов170 исключена из публикации. Причина символицирована: SourceAppearance.init:787 → presentation() → отсутствующий MediaPlayerNodeLayer.init(layer:). Удалены lookup и отдельная CA-анимация live видеослоя; [контракт и проверки](PIP_FIRST_REQUEST.md). Нужны новая чистая SDK-сборка и пакет. После их успеха повторно проверить собственный пустой draft и согласовать target с новым source перед защищённым owner publisher; старый source-run41971313591 для публикации не использовать. Не заменять опубликованные0.8.4/0.8.5 и не публиковать через токен бота.

Оригинальный проверенный ZIP сохранён также в `/workspace/.codex-release-086/original-actions.zip`, чтобы пережить очистку /tmp. Несекретные параметры восстановления — `/workspace/.codex-release-086/owner-release-recovery.json`; профиль можно использовать только после проверки owner и profile_verified. Содержимое credential-файлов не читать.

Повторная проверка PiP на iPhone после исправления обязательна; остальные физические проверки ожидаются: [сценарии0.8.6](DEVICE_CHECK_086.md). Подпись для установки выполняется отдельно.

## Опубликованная сборка0.8.5/build165

**Обычный релиз 0.8.5/build165 опубликован. Нативная компиляция и проверка скачанного release IPA пройдены. Физическая проверка на iPhone ожидается.**

[Успешная сборка, попытка 2](https://github.com/Mr-EFES/NagramiX/actions/runs/41734603786/attempts/2) · [Исходный ZIP с IPA и метаданными](https://github.com/Mr-EFES/NagramiX/actions/runs/41734603786/artifacts/13288720208) · [Релиз 0.8.5](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.5) · [Скачать IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.8.5/NagramiX-0.8.5-unsigned.ipa).

База Telegram-iOS **13.1.2**, commit `279f89e4d4f63f17227bf877dc3d8990f22ecd58`, минимум iOS15.0. Оба задания Actions завершены успешно 4 ноября 2026 года. Actor и triggering_actor — Mr-EFES. Режим clean_build/publish_release включён; восстановление кеша отключено, cold gate пройден.

## Проверенный пакет

- IPA: `NagramiX-0.8.5-unsigned.ipa`, **86539866 байт**.
- SHA256 IPA: `1386cf0a4610a50fd4d32de2061a056fc2ed3277fc8acd2f4e571fbd0e4041bb`.
- Исходник бинарного пакета: `a75ab958d67c6b0aea0ef214e27175da9ace8358`. Дальнейшие правки публикации и документации в main не меняют этот provenance.
- Оригинальный Actions ZIP: artifact **13288720208**, **86268157 байт**, SHA256 `cc3c009e8d6c24bc10ada00179d9996e1bcf607f0053d203cdc545d85a6b8006`. Получен через GitHub artifact tool, скачан без перепаковки и сопоставлен с digest API.
- В ZIP ровно три файла: IPA, `BUILD-PROVENANCE.txt`, `SHA256SUMS`. Локально подтверждены CRC, checksum, версия/build/источник, 6 ARM64/iPhoneOS Mach-O с iOS15+, отсутствие временных подписей и профилей, RU/EN, 31 мелодия и 8 иконок.
- Символы: Actions artifact `NagramiX-0.8.5-symbols-arm64`, ID **13287751850**. Отдельное локальное сопоставление UUID dSYM не выполнялось.

Статус: **native_compile_passed / package_verified / release_published_verified / device_pending**. Подпись для установки выполняется отдельно. Физические сценарии — [проверка 0.8.5 на iPhone](DEVICE_CHECK_085.md).

## Подтверждённая публикация

Релиз **433416662** опубликован **4 ноября 2026, 06:21:29 UTC**, draft=false, prerelease=false, latest. Автор и uploader каждого файла — **Mr-EFES**. Тег `v0.8.5` указывает commit `a75ab958d67c6b0aea0ef214e27175da9ace8358`, из которого собран IPA; последующие изменения main относятся к публикации и документации. Body содержит только утверждённое описание приложения.

| Файл | Asset ID | Байт | SHA256 |
| --- | --- | --- | --- |
| BUILD-PROVENANCE.txt | 708473521 | 219 | `7b75a7480e8ae1cc5ba45fea60e97100a5b67c8dcc6561db259d6d23c862f46e` |
| NagramiX-0.8.5-unsigned.ipa | 708473519 | 86539866 | `1386cf0a4610a50fd4d32de2061a056fc2ed3277fc8acd2f4e571fbd0e4041bb` |
| SHA256SUMS | 708473528 | 94 | `8b336e0c5c5a8aff26cc413c240d98bce596c8510065106038e2a35d5b1d9517` |

Все три файла повторно скачаны из опубликованного релиза. Их состав, размеры и digest совпали с исходным Actions ZIP; validate_unsigned_ipa повторно подтвердил версию/build/source, CRC/checksum/provenance, платформу и ресурсы. Проверены latest, источник тега, автор и uploader каждого файла. Повторно запускать publisher для этого опубликованного релиза нельзя: его замена запрещена.

Предыдущий HTTP401 uploads.github.com устранён официальным повторным входом GitHub CLI, подтверждённым владельцем через сайт GitHub. Исходный runtime GH_TOKEN работал для API, но отклонялся сервером загрузки. Для команды публикации выбран подтверждённый профиль CLI без приоритетного GH_TOKEN; общая среда и её credentials не менялись. Токены не запрашивались в чат, не извлекались и не коммитились. Пересборка приложения для этого не выполнялась. Порядок выбора профиля и защиты от замены файлов — [RELEASE_VERSIONING](RELEASE_VERSIONING.md).

## Сохранённый опубликованный 0.8.4

Релиз/tag/IPA **0.8.4/build162** сохранены: [релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.4), [успешная сборка](https://github.com/Mr-EFES/NagramiX/actions/runs/41355923502). Размер IPA **86523244 байта**, SHA256 `bf9bc20d42a130c2f211210636cab6f523882201df56be335581f57202d2efe4`. Его исходный provenance — `9d66a823b8b8af2bcaf663f9b9ead9db47843123`; свёрнутый корневой commit/tag `fd14548b7517c1619db44c9a1f6bbb9a55b48b9c` не подменяет исходник уже собранного пакета. Оригинальный ZIP: 86252784 байта, SHA256 `e87fe90aefdfbef8f0ac2c2363707472828f64e76f6c736707aec5da513c96e5`. Исторический автор/uploaders github-actions[bot] не менялись; старые assets не заменяются.

После публикации GitHub API подтвердил видимость **private**. Репозиторий закрыт; ручной [порядок переключения](REPOSITORY_VISIBILITY.md) сохраняется для следующих сборок.
