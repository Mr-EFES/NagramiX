# Подготовка сборки0.8.6

Попытка169 (run41946979343, source90e13a2f699a7e804aa95316c090bbb819890e26) прошла pre-SDK/cold gate и прежнюю ошибку Preferences, но завершилась ошибками типов/видимости нового архива в TelegramUI. IPA не получен. Исправлены публичные типы и обращение к настройке в двух UI-шаблонах; добавлен обязательный Swift module-boundary gate с воспроизведением трёх прежних ошибок. Прежние48 runtime checks/режим,50 fail-closed, свежая композиция и строгая локализация проходят. После восстановления среды продолжается следующая чистая попытка с публикацией по имеющемуся разрешению.

Попытка168 (run41928753756, source5b0755864a981f9682024540557baaf3fc30844a) прошла144 pre-SDK команды и cold gate, но завершилась ошибкой SDK в двух локализованных обработчиках удаления моделей. IPA не получен, публикации0.8.6 нет. Оба optional-self обращения исправлены; фактический метод проверен Swift6.3 в debug/-O, старый вариант воспроизводит обе ошибки. Следующая чистая попытка с публикацией разрешена той же командой владельца; точные сведения будут обновлены после результата.

Владелец разрешил чистую сборку IPA0.8.6 и обычную публикацию в репозитории. Подготовлены итоговые изменения, локальные source checks и свежая композиция overlay; Apple SDK и проверка нового IPA ожидаются. Режим: clean_build=true, publish_release=true, prerelease=false, от Mr-EFES. GitHub API подтвердил public, gh — владельца. Commit/push и Actions выполняются в рамках этой команды; после результата здесь фиксируются run/source/build/checksum/release. [PiP](PIP_FIRST_REQUEST.md) и остальные новые функции ожидают [физической проверки](DEVICE_CHECK_086.md). Исторические сведения ниже сохраняются.

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
