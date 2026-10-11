# NagramiX 0.5.2: подготовка чистой сборки

Пользователь авторизовал новую чистую ARM64-сборку для физического iPhone. Новая версия0.5.2; следующие новые сборки должны повышать patch-версию на1, даже после неудачи. Предыдущие releases/tags/assets сохраняются.

| Параметр | Состояние |
| --- | --- |
| Версия | 0.5.2 |
| База | Telegram-iOS13.0, `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838`, CURRENT |
| Сборка | Подготовка, clean_build=true |
| Публикация | Новый тестовый релиз, publish_release=true/prerelease=true |
| Повторное использование IPA | Нет, artifact_run_id пустой |
| Совместимость | iPhone ARM64, iOS15.0+; внешняя подпись |
| Source SHA / workflow / checksum | Будут заполнены после запуска и независимой проверки |

В пакет входят все накопленные изменения: завершение voice/round/view-once player, положительный autoplay default OFF, mixed recording continuity/lifecycle, диагностика auth notices, profile links, короткие настройки, оригинальные видео, high-quality фото, selection toolbar в readonly preview и unread count sorting во всех папках. [Краткая аннотация](../product/releases/0.5.2.md), [план физической проверки](IPHONE_TEST_0.5.2.md).

Предварительно: полный clean overlay436outputs соответствует проверенному исходному дереву, Swift grammar7изменённых файлов списка/настроек без ошибок;16обратных substitutions и4drift+rerun refusal без записи для unread overlay. Pythoncompile, release metadata, JSON и diff checks. На Linux нет Apple SDK; нативная компиляция выполняется в GitHub Actions. Компиляция не подтверждает поведение аудиосессии, Bluetooth, UI жестов, read receipts или все runtime crashes. Причина AUTH_KEY_DROP и сетевых часиков после enqueue не считается устранённой только по исходникам.
