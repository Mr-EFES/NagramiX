# PiP для YouTube и встроенного видео

Текущий путь — стадия48 `system_web_picture_in_picture` после `font_theme_contrast`. По уточнению владельца плавающее окно Telegram из стадии42 заменено системным PiP iOS: WebKit для существующего HTML-видео и AVKit для существующего AVPlayerLayer. Воспроизведение в фоне и при блокировке подключено к общей настройке фонового видео. [Реализация и проверки](SYSTEM_WEB_PICTURE_IN_PICTURE.md).

Сохранённые ключи `nagramix.video.pipSwipe` и `nagramix.video.backgroundPlayback`, их default ON, существующие кнопка/свайп/VoiceOver прежние. При включённом PiP YouTube разрешается независимо от отсутствующего/отключённого `youtube_pip`. При OFF сохраняется чтение текущей серверной конфигурации; добавленный свайп учитывает прежний kill switch. Новых checkbox, аннотаций, сетевого сервиса и извлечения URL потока нет.

Системное окно использует исходный плеер, позицию и авторизацию. Галерея скрывается после сигнала действующего системного PiP; отказ, устаревший callback и пятисекундный timeout не оставляют её скрытой. Возврат подтверждается фактическим присоединением исходного контроллера, без play/seek/reset. Обычные файловые/HLS видео продолжают прежний sample-buffer AVKit-путь и свои анимации.

Область разрешений стадии42 сохранена: secret/paid/ad/local/nonregular сообщения исключены, для страницы нужна прежняя возможность возврата. Фон включается для уже воспроизводимого контента при соответствующей настройке. Системный PiP удерживает свою аудиосессию независимо от обычного фонового режима; при закрытии снимается только его владелец. Реальные права аккаунта и доступность самого видео не изменяются.

## История примера Ghostgram

При подготовке42 исследован [Ghostgram main@2a6b082](https://github.com/ichmagmaus111/ghostgram/tree/2a6b08272b7da893f88986846022bafd0727df89). В [GalleryController.swift](https://github.com/ichmagmaus111/ghostgram/blob/2a6b08272b7da893f88986846022bafd0727df89/submodules/GalleryUI/Sources/GalleryController.swift), blob `b08236e428550ed7336be7542898baa45e4f1b1a`, `GGExtrasPolicy.forcesYouTubePictureInPicture` возвращает разрешённую GalleryConfiguration до чтения серверного `youtube_pip`. Приоритет перенесён на прежнюю настройку NagramiX.

В том snapshot WebEmbed не даёт sample-buffer layer, а WebView PiP отключён. Поэтому первоначальная42 дополнительно использовала `OverlayUniversalVideoNode` внутри приложения. Этот промежуточный путь не соответствовал уточнённой задаче о системном PiP/фоне и заменён48. Все26snapshots, исходный InstantPage native blob `741d3a964b797020b79c210395fe6816219930db`, обратимость42 и [исторический receipt](WEB_VIDEO_PICTURE_IN_PICTURE_CHECKS.json) сохранены; они описывают именно42.

Новая48 имеет статусы `source_checked / native_compile_pending / device_pending`. Linux-проверки не подтверждают реальные кадры WebKit/AVKit, сетевой YouTube или работу заблокированного iPhone. Проверки SDK и физическая приёмка — в следующей отдельно разрешённой сборке; опубликованный IPA0.9.5 прежний.
