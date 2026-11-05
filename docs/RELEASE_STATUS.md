# NagramiX0.8.6: попытка172 остановлена до SDK

Новая чистая [172](https://github.com/Mr-EFES/NagramiX/actions/runs/42078683279), sourceb0c60937cc793ed13c8363a606e00896099b3a1a, завершилась ошибкой17:54UTC5 ноября в первом новом тесте PiP. Swift/Xcode27.1 отклонил local weak var как never mutated при -warnings-as-errors. SDK не начинался, нового IPA и опубликованного релиза0.8.6 нет. Test-only исправление WeakGalleryProbe прошло85 checks/режим,13negative variants/режим,44fail-closed; post-port/import также проходят. Приложение/overlay не менялись. НовыйSwift/Xcode повторно не запускался, полная151 проверка ожидается вCI; локальный historical unwrap ограничен диском. ЕДИНСТВЕННЫЙ разрешённый запуск использован: следующая SDK попытка/Actions/rerun только по новой личной команде владельца. Draft435043558 и tag/assets не менялись.

# NagramiX 0.8.6/build171 — исправление PiP собрано и пакет проверен

По новой личной команде владельца готовится **новая чистая0.8.6 со всеми накопленными исправлениями**: temporary/copy/archive visibility/model menu и визуальный PiP. Локально прошли26 проверок, включая все новые стадии, и post-port/import. Остальной полный151 прогон остаётся обязательным в Actions до SDK; локальный historical unwrap упёрся в диск, не в assertion. Новая Actions готовится к запуску, нового IPA пока нет. Режим clean/publish=true, prerelease=false; owner authorization проверяется отдельно. Следующие сведения о171 остаются историческими и не описывают новый пакет.

Новая правка [PIP_VISUAL_HANDOFF](PIP_VISUAL_HANDOFF.md) согласует вход/возврат PiP, жесты, hidden-media и сохранение воспроизведения по двум утверждённым видео. **В IPA171 её нет**; новая SDK/device pending. Сборка/Actions/публикация этой задачи не запускались.

Правка [LOCAL_MODEL_MENU](LOCAL_MODEL_MENU.md) реализует утверждённые короткие названия Whisper/Vosk, проценты только до установки и native галочку выбранного ID. **В IPA171 её нет**; новая SDK/device pending, сборку этой задачи не запускали.


Правка [ARCHIVE_DELETION_VISIBILITY](ARCHIVE_DELETION_VISIBILITY.md) устраняет в исходниках скрытую ячейку сохранённого альбома после удаления оригинала. **В IPA171 её нет**; новая SDK/device pending. Ни сборку, ни Actions/rerun для этой задачи не запускали.


Последующая исходная правка [TEMPORARY_MEDIA_ACTIONS](TEMPORARY_MEDIA_ACTIONS.md) также **не входит в IPA171**: постоянная →A, кружки, архив после server deletion и обычные действия временных вложений. Новая SDK/device pending; Actions не запускались.


Последующая исходная правка [MESSAGE_COPY_AVAILABILITY](MESSAGE_COPY_AVAILABILITY.md) в этот IPA171 **не входит**; у неё compile_pending/device_pending. Следующая сборка только по отдельной личной команде владельца.

**native_compile_passed / package_verified / owner_publication_pending / device_pending**.

[Успешная сборка171](https://github.com/Mr-EFES/NagramiX/actions/runs/41991272414) · [Исходный ZIP с IPA](https://github.com/Mr-EFES/NagramiX/actions/runs/41991272414/artifacts/13405168153).

Оба задания Actions успешно завершились5 ноября2026,10:12:24UTC. Source `e07c143b174be87ebf7b77e920918c851a73beb0`, actor/triggering_actor Mr-EFES. Полный pre-SDK набор и cold gate прошли; чистая нативная компиляция без восстановления кеша завершена:9686 actions, SDK этап08:46:43–10:11:32UTC. База Telegram-iOS13.1.2, pin279f89e4d4f63f17227bf877dc3d8990f22ecd58, минимум iOS15.0. Позднейшие документы в main не меняют источник уже собранного IPA.

- IPA `NagramiX-0.8.6-unsigned.ipa`: **88424416 байт**, SHA256 `e0c5e93bf9dcb5f026376c981a58a4609947ba30c188b8df777c17d250a8cca3`.
- Оригинальный Actions ZIP: artifact13405168153, **88081499 байт**, SHA256 `e88ab08f39d435ee49765984202618dfc4c4bd2f21cc35b06eceea568df10a69`. Скачан без перепаковки, digest API совпал; CRC и ровно три плоских файла проверены.
- BUILD-PROVENANCE.txt:219байт, SHA256 `dcbca224302a4fac20641800550c32e8f1181997477c0c112c0ee8bab56641fd`.
- SHA256SUMS:94байт, SHA256 `549145831695afb420c3ad54b1e4e69536246b0d3301a16768915c096d16d853`.
- Независимый validate_unsigned_ipa подтвердил checksum/provenance/version/build/source,6 ARM64/iPhoneOS Mach-O, iOS15+,71 каталог по613 ключей настроек/debug,31 мелодию,8 иконок, отсутствие профилей/временных подписей.
- Символы новой171: artifact13406056676, ZIP166239668байт, SHA256 `ea36b824cb069e1d4556d22056c90b881a8ae5f09772a0f906771deabce4de5f`. Отдельное локальное сопоставление UUID новых символов не выполнялось.

## Публикация готового пакета ожидает входа владельца

Default runtime CLI подтверждает Mr-EFES для API, но uploads.github.com снова вернул401. Оставлен только собственный пустой draft435043558: authorMr-EFES, draft=true, tagv0.8.6, targete07c143b174be87ebf7b77e920918c851a73beb0. Файлов в нём нет, публичного релиза0.8.6 пока нет. Старый собственный пустой434878552 при PATCH target стал untagged; после проверки owner/empty/draft/source этот заменённый служебный черновик удалён. Опубликованные выпуски и assets не заменялись.

Официальный gh device flow запрошен заново, после проверки готового IPA. Owner profile /workspace/.codex-nagramix-owner-gh пока не подтверждён; коды/токены не сохраняются в Git. После входа проверить Mr-EFES и вызвать owner publisher с source-run41991272414 и исходным ZIP через env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR=<подтверждённый профиль>. Перед продолжением проверить состав draft: только свой пустой допускает обычный повтор; при частичной загрузке сначала сверить исходные digest/uploader и не перезаписывать файлы. Новый SDK запуск для публикации не нужен.

Устойчивый оригинальный ZIP171: `/workspace/.codex-release-086/original-actions.zip`; SHA выше. Recovery selector рядом указывает171, новый draft435043558 и неподтверждённый CLI profile. Старый170 ZIP сохранён только в task tmp для доказательств, запрещён к публикации.

## Причина падения170 и проверка устройства

Оба crash-отчёта170 символицированы по точному UUID IPA/dSYM `A616A3B2-D778-3FD2-87FC-A90312CF9BCF`: SourceAppearance.init:787 вызывает presentation() → QuartzCore → отсутствующий MediaPlayerNodeLayer.init(layer:) → SIGTRAP. Один стек пришёл через свайп, другой через кнопку. Удалены presentation lookup и отдельная cornerRadius-анимация sample-buffer слоя; оформление готовится без actions, переходом управляет AVKit.66 проверок/режим и6 отрицательных вариантов проходят; [полный контракт](PIP_FIRST_REQUEST.md).

170/run41971313591/source19bbb2b2a7f463315daa1fb4389a9605984206e9 публиковать нельзя. Её IPA SHA256 `b358b77b62450460902d19dd881a795df998a9d5a9550127e06af9fa1802f912`, ZIP artifact13394808694/SHA256 `fa5e1e8561aa4580178bde7d42f08cac1979dc9f9e13c30f839da2a1cd25949a`. Символы170 artifact13394818659/SHA256 `1530f9ce03e1e6565e06b689f423ac031a96333d19594ed601aa5d6f42e63788` совпали по UUID с обоими отчётами.

Повторная физическая проверка PiP171 по кнопке/свайпу и плавности на iPhone **ожидается**: [сценарии0.8.6](DEVICE_CHECK_086.md). Новые сборки и rerun только по отдельной личной команде владельца; текущую171 он отдельно разрешил продолжать, она завершена. После завершения публикации напомнить владельцу ручной Make private; видимость автоматически не менять.

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
