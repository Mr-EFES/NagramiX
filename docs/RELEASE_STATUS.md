# NagramiX 0.5.4: проверенный IPA опубликован

Нативная сборка, упаковка и тестовая публикация завершились успешно. Пакет независимо скачан и проверен; физическая приёмка на iPhone ожидается.

| Проверка | Результат |
| --- | --- |
| Версия / build | 0.5.4 / 88 |
| Исходный SHA / tag target | c44530eabe0d08a5b5182173a4c37d4fefabc568 |
| Workflow | [№88](https://github.com/Mr-EFES/NagramiX/actions/runs/38393655818), build и release success |
| Релиз | [v0.5.4](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.4), prerelease, не draft |
| IPA | [NagramiX-0.5.4-unsigned.ipa](https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.4/NagramiX-0.5.4-unsigned.ipa) |
| Размер | 85 414 344байта |
| SHA256 | 22770c8c8523cfac0815b7e0c4ac4dbad75e529474e77ce65b0feb9cb311f8ca |
| Платформа | ARM64, iOS15.0+, bundle com.mr-efes.nagramix, RU region, background audio |
| База | Telegram13.0, f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838, CURRENT |
| Входные параметры | clean_build=true, publish_release=true, prerelease=true, artifact_run_id пустой |

Независимая проверка `/workspace/.codex-validation-nagramix-054-build88-release`: SHA256SUMS и BUILD-PROVENANCE совпали с файлом, source SHA/pin/run; tag указывает на тот же commit; ZIP CRC цел. Все6Mach-O ARM64, minimum15.0/background audio подтверждены. Нет временных _CodeSignature/embedded profiles. Основной RU ресурс14863ключа; все274RU/200EN значений NagramiX побайтно по значению совпали с исходниками. Все31мелодии проверены; два новых onboarding PNG и26RU/EN Tour значений прошли штатный validator. Тело релиза совпадает с [русской аннотацией](../product/releases/0.5.4.md).

Попытка[№87](https://github.com/Mr-EFES/NagramiX/actions/runs/38393039193) завершилась до компиляции из-за повторного включения PNG в AppResources/Lib.data и ios_application.resources. Удалён второй владелец, добавлена точная проверка native glob/единственного AppResources. Assets/manifest/loader прежние; чистый proof453файла,452прежних относительно87, только BUILD изменён. Исправление проверено успешным Bazel analysis/compile/package№88 и наличием PNG в IPA. Версия обеих попыток0.5.4.

Включены свайпы настроек, архивная одиночная пересылка/рассылка/Save, proxy sync и DNS Telegram, onboarding, skip call rating и [исправления стабильности](STABILITY_AUDIT.md). Нативная компиляция10новых/изменённых функций подтверждена; device_pending сохранён. XCTest и физические AVFoundation/Photos/сеть/доставка/жесты не проверялись. Компиляция не доказывает отсутствие всех ошибок; [приёмка iPhone](IPHONE_TEST_0.5.4.md).

Следующий рабочий выпуск0.5.5 только по новой команде; повторы текущей версии сохраняют0.5.4. Операции этой сборки не удаляли старые releases/tags/assets. Финальная сверка API: релизыv0.5.4/v0.4.5 доступны, releasev0.5.3 возвращает404при сохранённом теге8c0c117; в начале задачи релизыv0.5.3/v0.5.1 присутствовали. Кто/почему изменил их состояние, не установлено; восстановление вне текущей сборки не выполнялось. Последующие commits документации не являются source SHA этого IPA. Требуется внешняя подпись, например SideStore.
