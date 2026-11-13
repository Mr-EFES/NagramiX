# Swift initializer кнопки применения шрифтов

В попытке207 прошли ранние Apple-проверки, все62стадии overlay и TelegramCore с исправленной обработкой optional. Основная компиляция остановилась в SettingsUI на одном вызове `ASDisplayNode.init(viewBlock:didLoadBlock:)`. Swift importer переименовал второй аргумент в `didLoad`; старое имя недоступно с Swift3.

Прежняя проверка читала настоящий Objective-C selector из заголовка, но её Swift-адаптер ошибочно сохранял имя `didLoadBlock`. Она даже отвергала правильный `didLoad` как отрицательный сценарий. Проверка Objective-C текста не доказывала импортированное имя Swift. Этот неверный адаптер исправлен.

Stage63 `release_096_font_node_compatibility` после62 меняет только `didLoadBlock: nil` на `didLoad: nil` в кнопке «Применить». Используется тот же designated initializer с двумя аргументами. Размер кнопки, её видимость в navigation bar, current/preview cards, draft, явное применение, шрифты, лицензии, цвета, статус-бар и настройки не меняются. Новых строк и ресурсов нет.

Один replacement и пять guards дают семь новых `.inc`;4350 прежних snapshots и планы неизменны. Guards сохраняют native ASDisplayNode.h/Subclasses, navigation-bar content, font model и manager. Полное дерево63 отличается только этим аргументом;20исторических манифестов43–62 восстанавливаются lossless.

Новая Apple-проверка перед большим ранним набором копирует verbatim настоящие два typedef, три initializer declarations, designated attributes и метод sizing из защищённых заголовков в отдельный Objective-C module. NSObject shell опускает посторонние протоколы и ivars; настоящий UIKit и Objective-C importer определяют Swift-сигнатуру. Полное приложение и реализация Texture проверяются отдельно SDK-сборкой. Исправленный production-node должен пройти, original207 с `didLoadBlock` обязан быть отвергнут именно по имени аргумента. Linux отдельно проверяет Swift-модель с правильным `didLoad` и unavailable/renamed старым selector; это не заменяет Apple importer.

Сохранены проверки размера и видимости кнопки,5407случаев полного preview/apply/layout потока,58проверок выбора шрифта и исходные мутации в debug/-O. Полный экран дополнительно typecheck-ится против UIKit с исправленным imported-label адаптером. Historical52 source/runtime и SHA не переписываются: native checks выбирают exact final63 UI только при известном input/output SHA, что явно указано в отчётах. Старый52 UI не объявляется пригодным для SDK.

Ранний набор остаётся27fixtures/54executions; initializer ABI проверяется первым дополнительным gate. Связанные исправления207 — только этот selector и точность тестов. Full application SDK/IPA и iPhone приёмка остаются отдельными результатами. Все опубликованные релизы сохраняются; повтор текущей0.9.6 разрешён владельцем до успешной публикации.
