# PiP для YouTube и встроенного видео

Stage42 `web_video_picture_in_picture` после `app_font_selection`. Команда владельца: изучить Ghostgram и добавить его поддержку YouTube под общий переключатель «Режим „Картинка в картинке“». Нового переключателя, аннотации, настройки или сетевого сервиса нет. Опубликованная0.9.4/build195 не меняется; новая IPA0.9.5 требует отдельной команды.

## Проверенный пример

Исследован [Ghostgram main@2a6b082](https://github.com/ichmagmaus111/ghostgram/tree/2a6b08272b7da893f88986846022bafd0727df89). В [GalleryController.swift](https://github.com/ichmagmaus111/ghostgram/blob/2a6b08272b7da893f88986846022bafd0727df89/submodules/GalleryUI/Sources/GalleryController.swift), blob `b08236e428550ed7336be7542898baa45e4f1b1a`, `GGExtrasPolicy.forcesYouTubePictureInPicture` возвращает разрешённую GalleryConfiguration до чтения серверного `youtube_pip`. В Extras policy флаг связан с пользовательской настройкой. Этот приоритет перенесён на существующий `NagramiXTabSettings.videoPiPSwipeEnabled`.

В проверенном Ghostgram обработчик кнопки запускает только `NativePictureInPictureContentImpl`, а WebEmbed не предоставляет sample-buffer layer; WKWebView PiP там также отключён. Поэтому одного копирования флага недостаточно для рабочего YouTube в нашей текущей цепочке. Добавлен отдельный путь для уже существующих `WebEmbedVideoContent`, `SystemVideoContent` и `PlatformVideoContent` через штатный `OverlayUniversalVideoNode` Telegram. Это плавающее окно **внутри приложения**. Оно не обещает системный PiP YouTube поверх других приложений или воспроизведение недоступного серверу, авторизованному пользователю либо сайту видео.

## Поведение

Общий сохранённый ключ `nagramix.video.pipSwipe` и default ON прежние. ON разрешает YouTube независимо от отсутствующего/отключённого `youtube_pip`, включает ту же кнопку и свайп для Vimeo, generic iframe и штатных AVPlayer-обёрток. Для сообщения используется существующая кнопка внизу; у страницы добавлена штатная кнопка с прежними ресурсом и VoiceOver-строкой. Клавиатурный переход также использует общий обработчик.

OFF не перезаписывает значение. YouTube возвращается к текущей серверной конфигурации: допускается строковое значение, отличное от `disabled`; отсутствие или неверный тип запрещают принудительное разрешение. Серверное значение перечитывается, поэтому ранее вычисленная принудительно разрешённая конфигурация не переживает OFF. Добавленный свайп работает только при ON и сохраняет серверный swipe kill switch. Обычные файловые/HLS видео используют прежние AVKit-кнопку, свайп, источник, clipping и переход фона.

Новый путь не применяется к secret, paid, ad, local/nonregular сообщениям либо странице без возможности возврата. Перед переносом проверяются центральная строка, живой владелец контента, layout, минимальный zoom, overlay host, presenter и отсутствие другого системного PiP. Проверки синхронные; состояние перехода блокирует второе нажатие. Если окно не присоединилось, состояние, placeholder и прежний callback восстанавливаются, разрешая повтор.

`OverlayUniversalVideoNode` запрашивает **тот же** content ID у **того же** UniversalVideoManager и исходного AccountContext с приоритетом overlay. Новый WebView, декодер, скачивание, извлечение YouTube-потока и новая авторизация не создаются. Техническая PiP-пиктограмма подавляется до передачи владения. Используются существующие анимации overlay и мягкого закрытия галереи; при отсутствии snapshot или нулевой геометрии переход завершается без force unwrap/деления на ноль.

Закрытие действует только на текущее окно; его живой контент ставится на паузу и отсоединяется. Callback старого окна не может закрыть новое. Потеря владения при разворачивании не ставит возвращённый плеер на паузу. Message gallery возвращается прежним маршрутом, с `fromPlayingVideo` для встроенного видео. Instant-page WebEmbed получает тот же callback возврата, который уже был у platform-video. Восстановление пропускает первоначальный play/seek, снимает отложенный autoplay и не перезагружает плеер.

## Границы и проверка

Три точные замены,20guards,26новых snapshots; все3483 прежних `.inc` сохранены. Новый native input InstantPageGalleryController подтверждён по [Telegram13.2 pin24638bc](https://github.com/TelegramMessenger/Telegram-iOS/blob/24638bc69bd083981b178dd1e7f921eebbf7fc46/submodules/InstantPageUI/Sources/InstantPageGalleryController.swift), git blob `741d3a964b797020b79c210395fe6816219930db`. Loader проверяет все зависимости/шаблоны до записи; stage зарегистрирован в обратимой цепочке и выполняется перед общими обязательными проверками workflow. Native AVKit/delegates/backdrop/clipping/visibility bodies сравниваются побайтно с предыдущим checkpoint.

Исполняются настоящие GalleryConfiguration/policy, полный start method, dispatch кнопки/свайпа, close closure и restore guards в debug/-O с явными адаптерами UIKit/media IO. Проверяются серверные комбинации, три типа плеера, ограничения, двойное нажатие, отсутствие владения/host/layout, rollback/retry, stale close и возврат без play/seek. Смысловые мутации должны отвергаться исполнением. Полный migration/inverse/member/localization/Postbox набор обязателен; результаты — [WEB_VIDEO_PICTURE_IN_PICTURE_CHECKS](WEB_VIDEO_PICTURE_IN_PICTURE_CHECKS.json).

Здесь Linux: Apple SDK, настоящий WebKit/AVFoundation, сеть YouTube/Vimeo, кадры/свайпы/звук на iPhone не проверены. Статус source_checked/compile_pending/device_pending. На следующей разрешённой IPA проверить сообщение со ссылкой YouTube, Vimeo/iframe, instant page, внешние mp4/m3u8, landscape/portrait, pause/resume/close/reopen, повторные свайпы, переход между чатами и ON/OFF. Обычный системный PiP должен сохранить прежние плавные края/фон и возврат.
