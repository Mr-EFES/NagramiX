# Telegram 13.1.1: перенос NagramiX

Включено в Release0.6.9/build122 на Telegram13.1.1: native_compile_passed/package_verified/device_pending. [Проверенный пакет](RELEASE_STATUS.md). Ниже — исходный контракт и история source-проверок.

Текущая база — Telegram13.1.1, commit `fb0e62ba8a147f0821da6aa63c09da7d79a10111`, Xcode27.1/Bazel9.2.0, minimum iOS15.0. Проверка актуальности официальной базы и точных SHA сохранена.

Исторический Telegram13.0/f1dd7 используется только как отдельный вход преобразования overlay и никогда не компилируется. Все canonical stages и325 input/445 output SHA остались неизменными. На настоящую базу переносятся351 выходной файл; manifest содержит78 рассмотренных контекстных разрешений с уникальными anchors и фиксированными final SHA. Все outputs готовятся до записи, конфликт/дрейф останавливает перенос.

Первоначальная миграция13.1/1dd3 разрешила38 конфликтных блоков в23 файлах и перенесла удалённый navigation header на новый API. API Postbox/Engine адаптирован без новых исключений import/access checks; подготавливаемые копии и доступ к retained bytes принадлежат Core. Native new-engine monitor/kill switch/liveness и NagramiX recovery lease объединены; политика iOS MTProto прежняя. Форматирование сохраняет structural selection, legacy/native backend, defaultOFF; Select All использует native facade.

Во время SDK119 официальный master обновился до13.1.1:8коммитов/62файла,16 пересекаются с портом. Они трёхсторонне слиты с уже рассмотренным результатом13.1. Единственный содержательный конфликт ChatHistory объединяет4 сигнала: видимая позиция, canRead, native holdsReadsForSender и настройки приватного чтения. Native запрет чтения до принятия подозрительного отправителя и сброс watermark при смене приватности сохранены вместе. Новые правила ссылок/кнопок подозрительных отправителей, MTContext cleanup, staysInRow и Duo layout сохранены.

Аудит run39860559228/job120109867351: полный guard replay351 outputs, сравнение34 373native файлов, полный branding CLI, mixed import/access preflight и PostboxImportCheck PASS. Metadata source commit616525b55190ae9c39bebff0150718d844f0af2d обновил только manifest и upstream.env. В логах — счётчики и контрольные суммы, без дампов исходников.

SDK115/116 выявил смешанные TelegramApi imports, implicit strong capture и отсутствующий Metal Toolchain. SDK117 выявил SaveToCameraRoll/CameraLegacy/TabBarUI: сохранение использует эквивалентный engine.resources.fetch, timer остаётся weak, native sidePlacement получает layout/itemCount. SDK118 выявил2 SettingsUI capture lists; внешние strong захваты теперь явные, внутренние weak callbacks прежние. SDK119 остановился на устаревшем upstream до компиляции. Эти правки включены в новый manifest; публичные ключи/defaults/поведение функций сохранены.

SDK120 выявил missing fromSkeleton в pinned emoji refresh; исправлено. SDK121 cached diagnostic PASS. Финальный SDK122/run39875592066 — clean_build=true, native/package/полноценный Release PASS; опубликованный файл независимо проверен CI и локально. Source/tag`6d867ccd1feb487f696adf10ed8cb4b5ae3ecefd`; последующие docs/CI коммиты не входят в IPA.

[Статус](RELEASE_STATUS.md) · [Физическая приёмка](DEVICE_CHECK_084.md). UIKit/сеть/авторизация/отправка на реальном устройстве остаются device_pending.

Локальный replay после исправления SDK120:351outputs/78reviewed edits, полный ожидаемый набор и34374 materialized файла побайтно проверены; каталог копии разворачивает upstream directory symlinks. Все native файлы вне manifest сохранены. Предыдущий CI audit34373 файлов остаётся отдельным доказательством; новый Core import preflight738 sources и Swift parse исправленного pinned файла PASS.
