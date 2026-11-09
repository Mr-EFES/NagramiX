# Выпуск NagramiX 0.9.1

Пользователь разрешил проверить накопленные правки, затем выполнить чистую сборку IPA и опубликовать обычный релиз в репозитории. Предыдущий порядок разрешает устранение причин сбоев и повторы этой версии до успешной сборки и owner publication; разрешение на каждый повтор не запрашивается. Новая версия после 0.9.1 требует отдельной команды.

Исходная main — `16c1bcf987ea883986d4f9fdd1c6d9f95a871eea`. В неё входят пять доработок после опубликованной 0.9.0: воспроизведение сохранённых кружков, скрытие служебной карточки PiP, панель скачивания до нижнего края, утверждённые карточки истории правок, восстановление медиассылок копий. Все исходники и неизменяемые snapshots сохранены в main. Итоговый source17 — `/workspace/scratch/copy-reference-recovery/source-working-1`, независимый actual apply совпал по 37 655 путям.

Перед запуском повторяются собственные suites пяти правок на точных checkpoint, общая миграция/import/parser проверка, обратная проекция, настоящие custom members и строгая локализация. Source-проверки не заменяют whole-module Apple SDK, UIKit/AVKit и iPhone. Предыдущая опубликованная 0.9.0 и её assets остаются прежними.

Сохранённая личная авторизация GitHub CLI подтверждена как `Mr-EFES`. Репозиторий по API public, ранее открытый владельцем; ассистент видимость не менял. Параллельных выполняющихся сборок нет. Native Telegram13.2 `24638bc69bd083981b178dd1e7f921eebbf7fc46` повторно CURRENT, Xcode27.1, iOS15+. Secrets не читаются и не выводятся; обязательные CI secrets проверяются штатным ранним gate.

Планируемые параметры: `artifact_run_id=""`, `clean_build=true`, `publish_release=true`, `prerelease=false`, main. Версия 0.9.1 фиксирована на весь разрешённый цикл. После dispatch проверить фактические SHA, actor/triggering_actor и номер run. Отслеживать выполнение до результата, не отменять по устаревшему названию шага. При ошибке исправить причину, повторить подходящие проверки и выполнить новую чистую попытку.

После успешного build/package/CI verify сохранить исходный ZIP артефакта без перепаковки, сверить версию/build/source/provenance/SHA256, выполнить `scripts/publish_owner_release.py` от владельца, проверить author/uploader/digest/tag/latest. Физическая приёмка на iPhone остаётся отдельной. После выдачи результата напомнить владельцу про Make private.

Текущий статус: `owner_authorized / source_checks_passed / sdk_pending / package_pending / publication_pending / device_pending`. Журнал выполнения и отчёты — `/workspace/.codex-release-091/`.

Для освобождения места удалены только сгенерированные embedded/bare-metal библиотеки локального Swift toolchain, не используемые Linux Foundation-проверками. Host Swift после очистки проходит typecheck. Исходники, snapshots, логи, старые IPA, dSYM, credentials и pinned inputs сохранены; inventory записан в task receipt.

Повторный source preflight успешен: все пять suites в debug/-O,467 Swift parse/50 migration guards/14 historical runtime/Postbox, inverse683пути/57negative, custom members7321full/206canonical, strict71×630/44 899 lookup на режим,28 owner/16 IPA-catalog/8 dependency tests и7native origins. Проверенные файлы приложения не менялись. [Точный receipt](SOURCE_PREFLIGHT_091_CHECKS.json).
