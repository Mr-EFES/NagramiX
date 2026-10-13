# Не спрашивать оценку звонка

Текущее состояние: включено в проверенный IPA0.5.4/build88, **compile_passed / device_pending**. [Сборка, source SHA и пакет](RELEASE_STATUS.md). Записи о локальных проверках ниже описывают подготовку до этой нативной сборки; физическая проверка остаётся отдельной.

Реализовано по запросу пользователя: implemented / compile_passed / device_pending. Включено в опубликованный build88; следующая рабочая0.5.5 только по отдельной команде.

## Поведение

NagramiX → Функции → Звонки, после подтверждения исходящего звонка: «Не спрашивать оценку звонка». Новый переключатель без справочного footer, со штатным шрифтом и switch. Поиск понимает название, «оценка звонка», «качество связи» и «звёзды».

Ключ `nagramix.calls.skipRating`: отсутствует → true. ON блокирует автоматическое окно оценки завершённого звонка. OFF разрешает штатный запрос, когда native call state содержит `reportRating == true` и настоящий CallId. OFF не заставляет показывать окно после каждого вызова, пропущенного или неудачного звонка без запроса оценки. Сохранённый OFF/ON не сбрасывается при холодном запуске; изменения других настроек не перезаписывают этот ключ.

Ручная оценка через действие сообщения о звонке работает в обоих режимах. Никакой фиктивной оценки или автоматического отправления звёзд не добавлено. Управление звонком, голос/видео, завершение, транспорт, debug-политика и conference переходы остаются native.

## Реализация

Foundation-only `NagramiXCallSettings` в уже существующем NagramiXMediaSettings предоставляет общую константу ключа и getter. Core/settings и native CallsUI читают один источник. NagramiXTabSettings содержит Bool/initializer/current/save, changed-only запись; UI entry stableId140 и position515, прежние IDs сохраняются.

В актуальном pinned `CallControllerNodeV2` обнаружена незавершённая интеграция: при `.terminated` вызывался `callEnded`, но имеющийся `presentCallRating` callback не вызывался. Этот callback теперь получает реальные CallId/isVideo только при reportRating. Прежний `callEnded(reportRating)` сохранён. Общий CallController сначала проверяет skipRating и native presentedCallRating duplicate guard, затем повторно проверяет skipRating перед созданием окна после прежней задержки0.5секунды. Так включение настройки во время ожидания подавляет запланированное окно. Native `callRatingController(userInitiated: false)` используется без изменения самого рейтингового контроллера/API.

`apply_skip_call_rating` идёт последним:3 full-SHA native входа и5 уникальных замен в памяти до записи. Добавлена только Foundation-only зависимость CallsUI; UI/Core циклических зависимостей нет. Manual rateCall entry points и серверный механизм отправки оценок не модифицированы.

## Проверки

Чистый proof `/tmp/nagramix-053-call-rating-checked-proof`:453outputs относительно expanded baseline452 (прежний archived-save449 +3 audited native call inputs),444 побайтно прежних,8 целевых изменений,1 новый preferences helper. Все предыдущие архивные сохранения, пересылки, свайпы, прокси и графика сохранены.

`/tmp/nagramix-validate-call-rating.py`:5 exact reverse замен восстанавливают3 native входа;3 drift-сценария и rerun отклонены до записи; IDs строк уникальны, RU/EN labels/search keys уникальны; ручные rateCall callbacks, service messages и archive save меню побайтно прежние. Grammar6 изменённых Swift sources PASS. Pinned audit включает PresentationCallManager (terminated CallId?/reportRating и public isVideo), CallController, NodeV2, прежний Node и CallRatingController. Python/metadata/diff checks PASS.

Apple SDK/typecheck, запрос оценки на сервере и реальное окно на iPhone не проверены. В compiled build86 эта функция отсутствует; grammar не заменяет нативную компиляцию.

## Приёмка следующей сборки

1. Чистая установка: переключатель ON; автоматическая оценка не появляется даже при native reportRating. Переключить OFF и перезапустить — остаётся OFF. Повторить с ON.
2. OFF + входящий/исходящий аудио/видеозвонок, для которого native state требует оценки: одно штатное окно с правильным CallId/isVideo. Завершение звонка и закрытие call screen без зависания. Проверить также голосовой, переведённый в видео.
3. reportRating false, nil CallId, пропуск, отказ, busy и неустановленное соединение: новых принудительных окон нет. Conference переходы продолжают прежние условия.
4. OFF при завершении → включить ON во время0.5секундной задержки: запланированная оценка не показывается. Повторные terminal updates не создают дубль.
5. Ручное «Оценить звонок» работает при ON и OFF; рейтинги отправляются только после действий пользователя. Проверить оценку, отмену и закрытие окна.
6. Поиск «оценка», «качество связи», «звезды», RU/EN, две темы, узкий iPhone и большой шрифт: label/switch доступны, другие строки не заменяются. Несколько аккаунтов используют ту же глобальную настройку, как остальные опции NagramiX.
