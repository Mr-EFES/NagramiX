# Жизненный цикл функций

`registry.json` — журнал реализации iOS, используемый при планировании и проверке релиза.

Служебные статусы: `specified`, `not_started`, `in_progress`, `implemented`, `compile_passed`, `device_pending`, `verified` и `not_applicable`.

Функция считается завершённой, только когда её запись iOS имеет статус `verified`, если явно не утверждено исключение.
