# Сборка 0.8.5/build165

**Нативная компиляция и проверка IPA пройдены. Публикация файлов GitHub Release пока не завершена. Физическая проверка на iPhone ожидается.**

[Успешная сборка, попытка 2](https://github.com/Mr-EFES/NagramiX/actions/runs/41734603786/attempts/2) · [Исходный ZIP с IPA и метаданными](https://github.com/Mr-EFES/NagramiX/actions/runs/41734603786/artifacts/13288720208) · [Собственный черновик](https://github.com/Mr-EFES/NagramiX/releases/tag/untagged-0a39f6e91f40f7fe6917).

База Telegram-iOS **13.1.2**, commit `279f89e4d4f63f17227bf877dc3d8990f22ecd58`, минимум iOS15.0. Оба задания Actions завершены успешно 4 ноября 2026 года. Actor и triggering_actor — Mr-EFES. Режим clean_build/publish_release включён; восстановление кеша отключено, cold gate пройден.

## Проверенный пакет

- IPA: `NagramiX-0.8.5-unsigned.ipa`, **86539866 байт**.
- SHA256 IPA: `1386cf0a4610a50fd4d32de2061a056fc2ed3277fc8acd2f4e571fbd0e4041bb`.
- Исходник бинарного пакета: `a75ab958d67c6b0aea0ef214e27175da9ace8358`. Дальнейшие правки публикации и документации в main не меняют этот provenance.
- Оригинальный Actions ZIP: artifact **13288720208**, **86268157 байт**, SHA256 `cc3c009e8d6c24bc10ada00179d9996e1bcf607f0053d203cdc545d85a6b8006`. Получен через GitHub artifact tool, скачан без перепаковки и сопоставлен с digest API.
- В ZIP ровно три файла: IPA, `BUILD-PROVENANCE.txt`, `SHA256SUMS`. Локально подтверждены CRC, checksum, версия/build/источник, 6 ARM64/iPhoneOS Mach-O с iOS15+, отсутствие временных подписей и профилей, RU/EN, 31 мелодия и 8 иконок.
- Символы: Actions artifact `NagramiX-0.8.5-symbols-arm64`, ID **13287751850**. Отдельное локальное сопоставление UUID dSYM не выполнялось.

Статус: **native_compile_passed / package_verified / release_upload_blocked / device_pending**. Подпись для установки выполняется отдельно. Физические сценарии — [проверка 0.8.5 на iPhone](DEVICE_CHECK_085.md).

## Завершение публикации

Создан обычный собственный черновик **433416662**, автор Mr-EFES, tag_name `v0.8.5`, target `a75ab958d67c6b0aea0ef214e27175da9ace8358`. Публикация остановилась до загрузки первого файла: CLI и стандартный SDK получают HTTP401 от uploads.github.com, хотя API подтверждает аккаунт владельца и позволяет создать черновик. На момент проверки в нём нет assets. GET по тегу не видит неопубликованный черновик; скрипт находит его в постраничном списке релизов и отклоняет неоднозначные совпадения. Не объявлять выпуск опубликованным до фактической проверки API.

Через браузер можно прикрепить к этому черновику три неизменённых файла из исходного ZIP. Затем агент завершает уже разрешённую публикацию:

```sh
python3 scripts/publish_owner_release.py --source-run-id 41734603786 --artifact-zip <оригинальный-ZIP> --finalize-uploaded
```

Режим проверяет CI, cold gate, ZIP, IPA, источник, полный набор assets, размер/SHA256 и uploader Mr-EFES до открытия релиза. Он не загружает и не перезаписывает файлы. Пустой, неполный, изменённый, чужой или уже опубликованный набор отклоняется. Новая SDK-сборка для завершения публикации не требуется; токены и коды в чат не запрашивать.

## Сохранённый опубликованный 0.8.4

Релиз/tag/IPA **0.8.4/build162** сохранены: [релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.4), [успешная сборка](https://github.com/Mr-EFES/NagramiX/actions/runs/41355923502). Размер IPA **86523244 байта**, SHA256 `bf9bc20d42a130c2f211210636cab6f523882201df56be335581f57202d2efe4`. Его исходный provenance — `9d66a823b8b8af2bcaf663f9b9ead9db47843123`; свёрнутый корневой commit/tag `fd14548b7517c1619db44c9a1f6bbb9a55b48b9c` не подменяет исходник уже собранного пакета. Оригинальный ZIP: 86252784 байта, SHA256 `e87fe90aefdfbef8f0ac2c2363707472828f64e76f6c736707aec5da513c96e5`. Исторический автор/uploaders github-actions[bot] не менялись; старые assets не заменяются.

После завершения публикации или остановки работы пользователь вручную закрывает репозиторий по [порядку](REPOSITORY_VISIBILITY.md).
