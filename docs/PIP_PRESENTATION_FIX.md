# Переход системного PiP без наложения галереи на чат

Текущий последующий контракт — [PiP без локальной миниатюры](PIP_NATIVE_TRANSACTION.md). После физического теста132 пользователь показал сохранённый shrink-source на чёрном fullscreen. Новая стадия убирает локальную геометрию жеста и зависимость didStart→dismiss от fade completion. Описанные ниже finger pose/freeze и389gesture-проверок относятся к прежней схеме.

## Запрос и наблюдение

После теста 0.7.3 пользователь показал уменьшенное видео поверх чата вместе с оставшимися полноэкранными Glass-контролами и полупрозрачной подписью/плеером. Нужны кнопка и свайп, штатный AVKit, фоновое воспроизведение, возврат и многократные portrait↔landscape без закрытия просмотрщика. Направление свайпа не управляет углом системного PiP.

Скриншоты подтверждают визуальное наложение, но не содержат стек нового вылета. Не заявлять, что по ним установлена причина любого краша или что исключены все будущие отказы AVKit.

## Что проверено по исходникам

Изучены [исходники Swiftgram](https://github.com/Swiftgram/Telegram-iOS/blob/master/submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift), blob `2e376fba95c067131e9c0095a2277ef7a16020b4`, и [документация Apple ContentSource](https://developer.apple.com/documentation/avkit/avpictureinpicturecontroller/contentsource-swift.class) / [восстановление UI](https://developer.apple.com/documentation/avkit/avpictureinpicturecontrollerdelegate/pictureinpicturecontroller(_:restoreuserinterfaceforpictureinpicturestopwithcompletionhandler:)). Swiftgram использует штатный AVKit с исходным sample-buffer layer и delegate восстановления; его отдельный внутренний плеер не переносился. Код проекта сравнен с source0.7.0 (`2af74be`): визуальный слой жеста существовал уже тогда, поэтому одного отключения hybrid_pip недостаточно, чтобы изменить этот путь.

Завершённые сессии уже исключались `nagramiXMatchesSource`: в ходе исследования первоначальная гипотеза их повторного использования была отвергнута. Этот guard не переписывался.

## Рабочая правка

Последний guarded stage `pip_presentation` после `quick_format_equal_spacing`,3nativeSwift-файла, полные SHA до/после и guard шаблона жеста. Ранние canonical-этапы сохранены.

- Во время drag фон галереи остаётся непрозрачным. Жест не раскрывает постер в чате и не смешивает его с уменьшенным видео/полноэкранным UI. Передача начинается из последнего положения пальца; общий fade галереи остаётся частью системного перехода.
- До движения и на willStart кнопки, scrubber и подписи скрываются штатным gallery setter без анимации. Общий host центральных Glass-контролов дополнительно скрывается на время передачи, чтобы незавершённая внутренняя анимация не оставляла кнопки над чатом. При отмене с видимыми ранее контролами host снова доступен ещё до завершения return-анимации; обычный player UI не заменён.
- `completeCustomDismiss` запрашивает UIKit-dismiss, но это не доказательство удаления view из окна. Прежний немедленный сброс трансформации после этого запроса убран. Последний source pose сохраняется до восстановления; существующий `nagramiXPreparePiPRestoration` сбрасывает его перед возвратом AVKit. На отказе/отмене прежний обратный переход и generation guards остаются.
- Убрано присваивание `dismissOnOrientationChange = item.landscape`. Обычный полноэкранный просмотр больше не закрывается по этому флагу при обратном повороте. Штатные Gallery/Pager/Zoomable aspect-fit/центрирование и их transition сохранены: видеокадр занимает максимально доступную область без растяжения/принудительной обрезки.
- Уже существующий сброс незавершённого жеста при изменении размеров сохранён. Во время native start/active источник не сбрасывается этим callback. Регистрация AVKit остаётся только в явной `.preparing`, не из layout/status/init.

Не добавлены второй decoder, AVPlayer, внутреннее плавающее окно, forced Play/seek при foreground или таймер анимации. Аудиосессия, ownership/Now Playing и восстановление failed/requiresFlush renderer прежние. Свайп по настройке и кнопка продолжают использовать один system-start path. Защитные ограничения secret/ad/unsupported media прежние.

## Проверки и пределы

- Production gesture с UIKit boundary doubles:389проверок в debug/optimized, отмена, отказ, фон, короткий/длинный drag, поздние callbacks, повторная передача. Вариант с прежним прозрачным фоном отвергается исполнением этих тестов.
- Реальное выражение видимости host проверено для swipe→cancel и native→restore, отсутствующего view, debug/optimized.
- Полная clean overlay-цепочка, SHA/anchors/template guard, source validators форматирования/кружков/system PiP и Swift parse пройдены.
- Штатные методы zoom-layout:7704проверки в каждом режиме, многократная смена ориентаций,6пропорций видео/4экрана, центрирование/aspect fit, pinch reset, передача animation transition. Вариант со старым viewport отвергается.

Доказательства `/workspace/.codex-validation-nagramix-pip-presentation/`, `/tmp/check_pip_presentation_full.log`. Это source/модельные проверки, не исполнение Apple AVKit/Glass/UIKit на iPhone. Новая композиция native_compile_pending/device_pending; опубликованный IPA0.7.3 не менялся. Actions/IPA/commit/push по этой задаче не выполнялись.

## Физическая приёмка следующей сборки

1. Native file/HLS, portrait/landscape/square: отдельно кнопка и свайп в каждой ориентации. Не остаются полноэкранные controls, подпись или второй анимируемый source поверх чата.
2. Короткий жест/отмена/ошибка старта возвращают кадр и прежнюю видимость controls, позицию/паузу/скорость; повторный запрос работает.
3. Не менее20 portrait↔landscape без PiP, затем те же переходы с началом/отменой жеста, возвратом из PiP. Кадр вписан в текущий viewport, нет ухода из галереи по обратному повороту.
4. PiP→lock→pause/play→unlock→Expand, обычное фоновое видео без PiP, быстрые Expand/Close/Back и другой ролик. Нет чёрного кадра или потери звука/управления; фактическое поведение фиксировать отдельно от model tests.
