# Размер локальной модели до загрузки

По последним трём скриншотам владелец уточнил состояния меню Whisper/Vosk. Это заменяет прежнее отсутствие подписи у любой не загружающейся модели: пустая правая часть допустима только после установки. Технические ID/footer/«Загружена» не возвращаются.

- Не установлена и не загружается: справа размер файла из существующего каталога. Он доступен при самом первом открытии без сети. Для Vosk это размер скачиваемого ZIP, для Whisper — файла весов; память распознавания и распакованный каталог не подменяют объём загрузки.
- Загружается: справа только текущий процент, включая0% и100% до завершения установки.
- Установлена: подпись отсутствует; native checkmark только у выбранного установленного ID. Установленность имеет приоритет перед запоздалым progress100%.

Сценарий третьего скриншота: установленная Базовая — галочка без подписи, Средняя загружается —53%, Максимальная ещё не скачана — размер. После отмены/удаления размер возвращается; галочка не переносится к загружаемой модели. Одинарная строка, прежний шрифт, native value1/RTL, короткие названия и отсутствие technical footer сохраняются.

## Реализация

Поздняя guarded стадия `local_model_size` после `archive_deletion_effect`:1replacementPreferences/16guards. Добавлен только presentation helper и его вызов для двух списков. Прежний percent formatter, footer, cell/checkmark code, модели/ID/размеры/URL/hash, загрузка/выбор/ревизии/удаление/consent/ASR и все другие строки сохраняются побайтно. Старые canonical snapshots не меняются. Предыдущее исправление первого удаления сохранено отдельным точным guardHistory.

Размер форматируется существующими public dataSizeString и DataSizeStringFormatting из TelegramPresentationData с текущими PresentationStrings.FileSize_B/KB/MB/GB и presentation decimalSeparator. Дополнительной зависимости TelegramStringFormatting не вводится: используется публичный конструктор уже прямой зависимости. Форматирование Telegram использует1024 для переключения единиц. Системный ByteCountFormatter, фиксированные русские/английские единицы и новые UI-ключи не используются;71×613 NagramiX каталоги прежние, native единицы следуют выбранному pack.

## Проверки

`validate_local_model_size.py`:3882 state/title/selection/layout/localization assertions в каждом debug и-O,6 отрицательных вариантов в обоих режимах,44fail-closed проверки. Выполняются реальные enum/каталоги и размеры, актуальные row/helper/footer/checkmark тела и штатный byte formatter. Для EN/RU единицы взяты из настоящих bundled строк; остальные native remote packs представлены явными wire sentinels, проверяющими выбор текущего объекта PresentationStrings. Человекочитаемые NagramiX названия проверяются по всем71 настоящим каталогам. UIKit/rendering и download IO — границы, физическая отрисовка не заявляется.

Проверены cold opening, mixed installed/loading/not-downloaded, отмена и swipe-удаление, все выбранные IDs, stale100%,0/отрицательные/большие progress, десятичный разделитель, native B/KB/MB/GB и Int64-объём. Отрицательные варианты отвергают прежний пустой idle, явное скрытие размера, размер вместо процента, размер установленной модели, неправильный объём каталога и единицы default-language. Весь изменённый Swift файл прошёл frontend parse. Guard-only совместимость первого удаления, PiP, старого меню, visibility, временных действий и ASR пройдена; source localization111files/594calls и71×613 catalog неизменны.

Свежая pinned13.1.2+legacy13.0 композиция с обеими новыми стадиями прошла. После точного7-file post-port совпала сincremental по603owned paths; против предыдущей задачи изменился только разрешённый Preferences, History83cb... первого удаления сохранён. PostboxImportCheck успешен. `/tmp/nagramix-local-model-size/{validation.json,composition.log,final-composition-hashes.json}`, source `/tmp/nagramix-local-model-size/fresh`. Dummy API config только source validation, никогда неIPA. Удалён только проверенный superseded generated `/tmp/nagramix-pip-visual-handoff/fresh`, его602SHA manifest сохранён; оригинальныйtar, cleanlegacy, текущие source, IPA и символы не удалялись.

**Source_checked / native_compile_pending / device_pending.** Новая правка не входит в опубликованную0.8.7/build173. SDK/Actions/rerun/IPA/commit/push не выполнялись; следующая сборка только по отдельной личной команде владельца.
