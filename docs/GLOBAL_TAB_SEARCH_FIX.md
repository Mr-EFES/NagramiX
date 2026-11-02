# Кнопка поиска на всех основных вкладках

Статус: **source_checked / native_compile_pending / device_pending**. Правка подготовлена после физического теста0.5.5/build89 на iPhone17ProMax/iOS27.0. Опубликованный IPA89 не менялся; новая сборка не запускалась.

## Подтверждённые причины

Пользователь включил «Показывать кнопку поиска», оставил видимыми «Контакты» и «Звонки», выключил кнопку прокси и скрытие её спонсора. На экране звонков видны четыре обычные вкладки, но поиска нет.

В Telegram13.0 search у TabBarComponent создаётся из `currentController.tabBarSearchState.flatMap`. CallListController и ContactsController не устанавливают это состояние: у них nil. Проверка NagramiX showSearchButton стояла внутри flatMap и поэтому не могла добавить кнопку на этих вкладках. Кроме того, штатный CallListController.tabBarActivateSearch вызывает beginCallImpl: просто показать кнопку с прежним callback означало бы начать звонок вместо общего поиска.

Params кэша TabBarControllerNode включал геометрию/toolbar/текущее search state, но не сохранённый showSearchButton. При смене только переключателя одинаковые Params могли вернуть прежнюю отрисовку, даже после root updateLayout. Проверенный native TabBarComponent допускает search вместе с четырьмя items: резервирует отдельную ширину и использует стандартную NavigationSearchView, ограничений по количеству вкладок нет.

## Исправление

TelegramRootController подключает существующий ChatListController как слабую цель общего поиска и callback с weak root. Нажатие использует штатный openChatsController(activateSearch:true): выбирает «Чаты» по identity/type в актуальном наборе вкладок и открывает существующий поиск. Нет нового контроллера поиска, дополнительной вкладки, фиксированного индекса или собственной клавиатуры.

TabBarControllerImpl передаёт цель в node и направляет активацию к общему поиску только при root binding; прочие экземпляры сохраняют native current-controller fallback. Deactivate остаётся штатным. Binding выполняется при первоначальном построении, обновлении списка и мягком перезапуске панели. Слабые ссылки не удерживают старый root/account.

Node создаёт Search при сохранённом ON даже если текущий экран не поддерживает локальный поиск. Кнопка доступна на «Контактах», «Звонках», «Чатах» и «Настройках», независимо от прокси и числа скрытых вкладок. При OFF кнопка отсутствует. Активное состояние общего поиска отображается только на целевом ChatListController; локальный поиск настроек/контактов не выдаётся за общий. Поисковое состояние текущего экрана для native keyboard/layout сохраняется.

Три поля добавлены в Equatable Params: showSearchButton, наличие общей цели и текущий экран этой цели. Изменение переключателя инвалидирует прежний результат даже при тех же размерах; прежний observer settings вызывает штатный updateLayout. Ключ nagramix.tabs.showSearchButton и defaultOFF, сохранённый ON/OFF, контакты/звонки/proxy/sponsor/title settings и selected-controller identity не меняются. Геометрия/иконка/VoiceOver/тема остаются штатными TabBarComponent.

## Проверки и границы

`apply_global_tab_search_fix` после правки PiP:3full-SHA guarded native файла,13точных замен до записи. Root SHA ecbbc6199782446a09d626f2b446aab9ed1d003b9c51ab1a18bbe94d3da483f8, TabBarController SHA65c528ab7126dd1f84f547cd3173511a815c1988117c676bd31a06c65c874a74, Node SHA55350cd6d1015f137030d1eeaf4ad4761acdb6f698fd71a43b0ae82be8a08fc5. Native controller получен из audited pin f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838, Git blob a71c2b09de7d0ea796e937435d406487295d9c2f проверен.

`scripts/validate_global_tab_search.py`: scope3native/13exact reverse/cache fields/global activation/native fallback/weak ownership,3SHA drift и повторное применение без частичной записи PASS. Полный overlay на чистой базе461outputs совпал461/461 со scoped proof; остальные458output побайтно прежние, включая подготовленную правку поворотов/PiP. Три Swift файла grammar/Pythoncompile/metadata/diff PASS. Native Apple SDK compile и реальное UIKit взаимодействие не выполнялись. Registry tabs compile_pending/device_pending до новой сборки.

## Приёмка следующей сборки

1. Исходный набор из скриншота: контакты/звонки видимы, поискON, проксиOFF, скрытие спонсораOFF. Отдельная кнопка поиска есть на всех четырёх вкладках.
2. Нажатие из каждой вкладки открывает штатный общий поиск в «Чатах», позволяет ввести запрос и открыть результат; со «Звонков» не запускает новый звонок. Cancel/закрытие работают штатно.
3. ON→OFF→ON без выхода из приложения и без поворота экрана сразу скрывает/показывает кнопку; повторить при неизменном наборе вкладок, после мягкого перезапуска и холодного запуска.
4. Все четыре комбинации видимости контактов/звонков, проксиON/OFF, поискON/OFF: правильные вкладки и один поиск, сохранение ручных значений. Начальные defaults не сбрасываются.
5. Темы/размер текста/VoiceOver, portrait/landscape, локальный поиск настроек и контактов, поиск с клавиатурой: прежние layout/insets и кнопки отмены. Повторить сценарии поворотов видеоплеера из VIDEO_ROTATION_PIP_FIX.
