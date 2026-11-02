# Оформление кружков, битрейты и условный киноэффект

Последующая доработка: [независимый регулируемый битрейт1,0–2,0Мбит/с и сохранение codec/bitrate в записи](ROUND_VIDEO_BITRATE.md). Фиксированные профили ниже описывают предыдущую версию.

Актуальный результат: эта правка вошла в0.7.5/build134/sourcefe620c5f7c2463882455d1609622779db8b3239c. SDK и публичный IPA проверены; физическая приёмка ожидается. Ниже описан также предшествующий этап source-проверок. Подробности — [RELEASE_STATUS](RELEASE_STATUS.md).

По физическим скриншотам132 у самостоятельной страницы кружков были чёрные часы/индикаторы на тёмном фоне и крупные жирные стандартные заголовки UITableView. Пользователь утвердил1,0/1,2/1,5Мбит/с и раздел «Киноэффект» с «Да / Нет» только при30FPS и поддержке телефоном. Эта правка заменяет соответствующую часть [ROUND_VIDEO_PAGE](ROUND_VIDEO_PAGE.md); прежний опубликованный пакет не меняется.

## Интерфейс

Строка состояния получает `presentationData.theme.rootController.statusBarStyle.style`, как штатный ItemListController. В тёмной теме часы/индикаторы белые, в других темах используется штатный цвет. Сам navigation bar, Назад и фон темы сохраняются.

Размер берётся из PresentationData.listsFontSize, как в native ItemListPresentationData initializer; поле fontSize существует у другой обёртки, не у PresentationData. Заголовки используют Font.regular/itemListBaseHeaderFontSize и theme.list.sectionHeaderTextColor, как ItemListSectionHeaderItem. При обычном размере приложения это13pt/regular вместо крупного системного жирного заголовка. Основные строки — itemListBaseFontSize, подписи — floor(base×15/17), как ItemListCheckboxItem. Учитывается выбранный в приложении размер текста, доступны переносы; темы/палитры не подменяются. Новый import ItemListUI использует уже существующую зависимость SettingsUI BUILD.

«Киноэффект» виден только при30кадрах/с и подходящем реальном формате камер для выбранного разрешения. При60 либо отсутствии поддержки раздел полностью отсутствует. «Да / Нет» используют прежнюю галочку. Выбор60 выключает эффект и убирает раздел; возвращение30 показывает доступный раздел с выключенным эффектом. Остальные параметры сохраняются. Устаревшее нажатие на скрытый раздел игнорируется. При открытии страницы неподдерживаемый прежний cinematicON очищается.

Смена видимости добавляет/удаляет только секцию3 без анимации. Число секций меняется внутри performBatchUpdates; прочие ячейки сохраняются, reloadData/reloadRows и пересоздания экрана нет. DataSource назначается после вычисления доступности начального раздела.

## Реальные параметры

| Уровень | Разрешение | Средний битрейт |
| --- | --- | --- |
| Стандарт | 480×480 | 1,0Мбит/с |
| Высокое | 512×512 | 1,2Мбит/с |
| Максимум | 640×640 | 1,5Мбит/с |

Одинаковые значения записаны в Camera и NagramiXMediaSettings, используются фактическим AVVideoAverageBitRateKey VideoRecorder и экспортом MediaEditorValues для deferred/trim. Подписи качества вычисляются из той же модели.30/60FPS, H.264/H.265 и round metadata прежние; выключенная функция использует штатный путь с прежним fallback битрейтом.

Старые ключи, master defaultOFF и уровни сохраняются. Init/read/update нормализуют cinematic при60 в false; оба Cinematic helper проверяют30 также на backend. Сохранены проверки iOS26+, actual formats/FPS/NV12/min side, выбора реальной камеры и поддержки input. Форматы60 могут быть использованы для30, если их диапазон допускает30; устройство должно реально поддерживать эффект. Стандартная проверка недоступных60FPS при записи с уведомлением пользователя остаётся.

Средний битрейт — параметр энкодера, а не обещание точного размера файла или серверного round-типа. Этот контракт не объявляет минутный HEVC-кружок проверенным без отправки реального файла.

## Проверки

Последний guarded stage round_video_refinement после pip_native_transaction:6Swift-файлов/6exact ops,4templates и10guards, включая штатные UI fonts/status implementation, BUILD, encoder и round sender. Ранние stages не меняются; source validators прежней страницы/панели признают только точные SHA позднего результата.

`scripts/validate_round_video_refinement.py --source <native> --swiftc <compiler>`:12actual capture/export presets, сохранение настроек/defaultOFF/legacy60 flag;24перехода реальных методов страницы с допустимым batch-count, поддержкой/30/60, сохранением прочих ячеек и offset, Yes/No, stale tap и masterOFF;36actual format predicates с AVFoundation boundary, fallback camera и4Ksource. Всё debug/optimized. Source guards сверяют stock status/header/row style; Swift parse и полная clean overlay-цепочка с прежними проверками проходят.

Proof `/workspace/.codex-validation-nagramix-round-refinement/`. Статус source_checked/native_compile_pending/device_pending: эти проверки не исполняют UIKit/AVFoundation/Photos на iPhone. SDK/IPA/Actions/commit/push не запускались, версия/README прежние; в исходнике132 этой правки нет. Физически проверить строку состояния/заголовки, 30↔60 приYes, поддерживаемый/неподдерживаемый телефон, сохранение после Назад/перезапуска и файлы всех quality/FPS/codec.

SDK-сборка133 выявила три неверных обращения PresentationData.fontSize в новом оформлении; исправлено на реальное listsFontSize. Добавлены guards исходных PresentationData/PresentationFontSize, проверка всех UI font accesses по реальным stored properties, компиляция21выражения с native enum/extension и отрицательная проверка старого no member fontSize. Source/model проверки раньше не покрывали этот API и не подтверждали SDK-компиляцию. Следующая чистая попытка остаётся версией0.7.5, поскольку публикации ещё нет.
