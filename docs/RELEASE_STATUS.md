# NagramiX 0.5.3: новая чистая сборка запущена

Предыдущая попытка [№85](https://github.com/Mr-EFES/NagramiX/actions/runs/38166584585) завершилась failure на native compile, релиз skipped, IPA не создан. Исходный SHA той попытки `6d7407102c754c6b7c86503525fd874a55a26574`.

Точный диагноз Apple Swift compiler: `ApplicationContext.swift:791:65: cannot assign value of type 'ViewController' to type 'AlertController'`. Factory `textAlertController(context:...)` возвращает `ViewController`; добавленная weak property ошибочно имела более узкий тип. В durable overlay исправлен только тип `nagramiXAuthorizationAlert` на `ViewController?`, без force casts. Weak ownership, Cancel/Logout, localization, dedupe/cooldown и native auth/logout paths прежние.

По постоянному правилу пользователя новую компиляцию нельзя повторять той же версии: готовится0.5.3. Предыдущие releases/tags/assets сохранены.

| Параметр | Состояние |
| --- | --- |
| Версия | 0.5.3 |
| База | Telegram-iOS13.0, `f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838` |
| Сборка | №86, [workflow](https://github.com/Mr-EFES/NagramiX/actions/runs/38176187919), queued/in_progress, clean_build=true |
| Публикация | Новый тестовый релиз, publish_release=true/prerelease=true |
| Повторное использование IPA | Нет, artifact_run_id пустой |
| Совместимость | iPhone ARM64, iOS15.0+; внешняя подпись |
| Исходный SHA новой сборки | `8c0c117647ae26c444965689773f1ae77a151f99` |
| SHA256 IPA | Ожидается после успешной компиляции |

Clean overlay `/tmp/nagramix-053-auth-controller-fix-proof`:436outputs,435побайтно прежних; единственное отличие — точный тип weak property в ApplicationContext. Обратная замена восстанавливает исходник попытки №85. Swift grammar прошла; это не Apple SDK typecheck, новую нативную компиляцию необходимо дождаться. Все накопленные функции сохраняются: [аннотация](../product/releases/0.5.3.md), [физическая проверка](IPHONE_TEST_0.5.3.md). На iPhone проверять также реальное аудио/повторные записи, server auth и network clocks; их runtime проблемы не объявлять устранёнными только по компиляции.
