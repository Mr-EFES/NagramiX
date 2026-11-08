# NagramiX 0.9.0 — опубликованный релиз

**Команда на выпуск 0.9.0 выполнена: native_compile_passed / package_verified / owner_published / device_pending.** Обычный latest [релиз0.9.0/build187](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.9.0) опубликован8 ноября2026 в17:07:26UTC; [IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.9.0/NagramiX-0.9.0-unsigned.ipa), [Actions](https://github.com/Mr-EFES/NagramiX/actions/runs/42485515942). Source/tag `76b232c120674a70bfc3f4afabd31810411a9b03`, Telegram13.2, Xcode27.1, iOS15+/ARM64. Автор и uploader всех трёх файлов — Mr-EFES; source/tag/latest/размеры/SHA256 подтверждены API. Все73 реализованные функции имеют compile_passed, физическая приёмка остаётся pending. Следующая новая версия —0.9.1, только по новой личной команде; успешная публикация исчерпала разрешение на повторы0.9.0. Ниже сохраняется история подготовки, которая не разрешает новый SDK/Actions/rerun.

IPA: **93 819 099 байт**  SHA256 `be173c213c97b883d77296369c154300a06911fb9494555b683418cc2e37fe8f`. Проверены0.9.0/build187  iOS15+/ARM64/iPhoneOS 6 Mach-O  RU15004/630 71 ресурсный каталог по630 ключей 31 мелодия 8 иконок и отсутствие временных профилей. Число каталогов включает варианты и не означает число официальных языков Telegram. IPA не подписан.

Оригинальный ZIP: artifact13626622374,93 425 168байт,SHA256 `cfdd1fd318b91233899e22797ea3b5a719ef1609d28c9de07037bb6e4f46614f`, без перепаковки. Release438390536: IPA724607605, provenance724607609, checksums724607604. Автор всех файлов Mr-EFES, normal/latest и tag подтверждены. Файлы и журналы `/workspace/.codex-release-090/`; [receipt](RELEASE_090_PUBLICATION_CHECKS.json).

186 прошла source/cold gate, но SDK выявил пропущенные import/public alias в «По автору» и timeout большого initializer. Stage12 исправлена и повторно проверена,187 завершилась успешным SDK/пакетом/публикацией. Прежние опубликованные релизы и assets не менялись. [Приёмка на iPhone](DEVICE_CHECK_090.md) ещё предстоит.

Символы именно187: artifact13626600642,203 084 268байт,SHA256 `e45d02d67b4d2fe3c68ee79f92642875aa43d1acee30c4900106fdc5dcde13e5`; сохранены без распаковки в `/workspace/.codex-release-090/symbols-build187.zip`, FileServiceID `file_0000000075b881f48f7411a30122534f`, тот же source/run. Это отдельный диагностический архив, состав трёх release assets не меняется.

## История подготовки0.9.0

**0.9.0/build186: source/cold gate passed, SDK failed, IPA отсутствует.** TelegramUI обнаружил пропущенный import и аннотацию типа в «По автору», а также timeout большого initializer. [Исправление stage12](RELEASE_090_SDK186_FIX.md) проверяется перед разрешённым чистым повтором этой же версии. Сведения ниже о выполняющейся186 исторические. Последним опубликованным остаётся 0.8.9/build185.

**Новая личная команда на сборку и публикацию 0.9.0 получена.** Проверенный код находится в main; разрешён чистый SDK/Actions-запуск и исправления/повторы до успешного IPA с обычной owner publication. Прежние запреты ниже относятся к завершённой подготовке. Личный вход восстановлен; [сборка186](https://github.com/Mr-EFES/NagramiX/actions/runs/42472042232) выполняется от Mr-EFES, clean=true/publish=true/prerelease=false, source `08550222185d4d27cc17eb6f0bb66094ca2771ac`. Новый IPA ещё не получен. Журнал — [RELEASE_090_RUN](RELEASE_090_RUN.md). Последний опубликованный релиз пока 0.8.9/build185, его файлы не меняются.

Восемь исправлений восстановлены, объединены и прошли source gate перед отправкой в main по отдельной команде владельца. SDK/IPA/Actions и публикация 0.9.0 не запускались и пока запрещены. Сводка и точные SHA: [PREPARATION_090](PREPARATION_090.md), [CHECKS](PREPARATION_090_CHECKS.json). Последний опубликованный IPA — 0.8.9/build185, его файлы и тег не меняются.

## Последний опубликованный выпуск 0.8.9

**Команда на выпуск 0.8.9 завершена: native_compile_passed / package_verified / owner_published / device_pending.** Обычный latest [релиз 0.8.9/185](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.9) опубликован 7 ноября 2026 в 19:24:08 UTC. [IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.8.9/NagramiX-0.8.9-unsigned.ipa), [Actions](https://github.com/Mr-EFES/NagramiX/actions/runs/42390556415). Исходник и tag v0.8.9: `1584858a852baa6003982f8c99fbdbce57a74d6c`; официальная база Telegram 13.2: `24638bc69bd083981b178dd1e7f921eebbf7fc46`, Xcode 27.1. Все проверки до SDK, cold gate, нативная ARM64-компиляция 17:38:17–19:21:25 UTC, упаковка, независимая CI-проверка и локальная проверка IPA прошли. Автор релиза и uploader всех трёх файлов — Mr-EFES; API подтвердил latest, source/tag, SHA256 и размеры. Наработки находятся в main. Физическая приёмка на iPhone ожидается по [DEVICE_CHECK_089](DEVICE_CHECK_089.md). Команда на этот выпуск исчерпана успешной публикацией; следующая новая версия — 0.9.0, только по новой личной команде. Документационные коммиты после сборки не меняют tag/IPA и не разрешают новый SDK-запуск.

IPA: **93 771 547 байт**, SHA256 `b1c2950e2ac92dda63c21885aa28adeb78a00bebf1fb554a0b3dd57c121fbbda`. Проверены версия 0.8.9/build185, iOS15+/ARM64/iPhoneOS (6 Mach-O), RU15004/629, 71×629 каталогов настроек/debug, 31 мелодия, 8 иконок, отсутствие временных профилей, checksum/provenance. В provenance явно указана закреплённая замена недоступного upstream tgcalls c1de0882 на официальный опубликованный38dcea12; остальные11native refs сохранены. Поведение на физическом iPhone, включая звонки и анимации, не объявляется проверенным.

Оригинальный Actions ZIP: artifact13586624612, **93 354 386 байт**, SHA256 `5b5dd6aaa1d1d68d55a747533d4da3d5d50a029b99125d2f511aa51e02d7083b`; сохранён без перепаковки в `/workspace/.codex-release-089/original-actions-build185.zip`. Три проверенных файла — `/workspace/.codex-release-089/verified-build185/`. Release437790356: provenance721694490, IPA721694494, checksums721694491. FileServiceID `file_00000000f5cc8243bc55e0611599d5b4`. Символы именно185: artifact13586907420,202975872байт,SHA256 `05edd5b1de7b1d064625eb7ad8aa595fe70fa548b513156fcfc4b2cbca8482cd`,тот жеrun. Символы и IPA прежних сборок не подменяют185.

До main/push был завершён полный локальный gate и зафиксированы точные SHA кода; отправленные байты совпали с проверенными. Независимый replay всех6SDK stages поверх ранее выполненной полной pipeline-композиции дал37641файл и0отличий. Ранний audit165snapshots и полный audit7320Swift/845string accesses сверяют реальные244объявления; компилируются233реальных getter и11функций с production ACK method/caller и71переводом ошибки. Прежние две опечатки отвергаются и compiler-negative проверками. Пройдены47migration guards/423parse/14PiP-R1-R2-R3runtimes, strict71×629/44828lookup на режим и все сохранённые CI-команды. Доказательства, receipt API и журнал публикации — `/workspace/.codex-release-089/`.

После скачивания и проверки IPA владелец вручную возвращает репозиторий в Make private: https://github.com/Mr-EFES/NagramiX/settings#danger-zone. Автоматически видимость не переключать. Сохранённый ownerCLI-профиль проверен и использован для всех трёх upload; credentials не читать и не выводить.

## История подготовки 0.8.9

Следующие записи описывают состояние на момент неуспешных попыток; их pending-статусы закрыты успешной185.

**Попытка 184 устранила прежний timeout, но SDK выявил две одинаковые опечатки в имени строкового свойства.** Прежний узкий fixture сам определял несуществующий member и ошибочно пропускал несовпадение; это не было подтверждением настоящего API. Новый `upstream_13_2_release_string_compile` заменяет только два `nagramiXArchiveCopyUnavailable` на реально объявленный `nagramiXArchivedCopyUnavailable`; 2 файла/4 guards. Тест теперь компилирует настоящие `NagramiXPresentationStrings.swift` и `NagramiXAppLocalization.swift` вместе с production ACK method/caller: 233 свойства,11 функций,71 перевод ошибки,4 исполнения debug/-O; обе прежние ошибки воспроизведены компилятором в каждом режиме.14 fail-closed passed. Полный аудит7320Swift:845 строковых обращений/229имён против244реальных объявлений,766custom declarations; неизвестных custom member names нет. Ранний canonical audit165финальных snapshots/299обращений отвергает обе старые опечатки до длинных CI checks; полный аудит повторяется на реальном дереве. Независимое применение всех6SDK stages к ранее реально собранному pipeline даёт37641файл,0отличий от проверенного кандидата; исходный pipeline сохранён. Повторно passed47migration guards/423parse/14PiP-R1-R2-R3runtimes/Postbox/strict71×629/44828lookup на режим,metadata/build-mode/28owner/8dependency/6IPA-catalog checks. По повторному указанию владельца новые main/push/SDK допускаются только после полного зелёного локального gate; receipt exact code hashes записан до push. Успешный полный Xcode/IPA и physical device ещё pending; повтор0.8.9 и owner publication до успеха остаются разрешены.

**Попытка 183 прошла все проверки до SDK и cold gate, но прежнего упрощения ACK оказалось недостаточно:** осталась одна ошибка type-check timeout в `accepted.indices.contains` внутри большого вложенного обработчика отправки; три ошибки API из попытки 182 больше не повторились. Новый `upstream_13_2_release_ack_compile` меняет только два файла: целиком выносит обработчик ACK в отдельный метод, явно задаёт тип Signal и заменяет ternary/contains на простой `if` по числовому индексу. Порядок, частичные результаты, корреляции, ошибки и условие показа успеха сохранены; эквивалентность перемещения проверена. 14 fail-closed, реальные обработчик и отложенный caller в debug/-O, 6 отрицательных семантических вариантов и weak lifetime passed. Полное дерево 37 641: ровно два отличия, прежняя композиция сохранена. Повторно passed: 47 migration guards, 423 Swift parse, 14 PiP/R1/R2/R3 runtime исполнений, native Postbox и strict 71×629/44 828 lookup checks на режим. Локальный scope не воспроизводит whole-module SDK timeout; нужен успешный полный Xcode build. Повтор 0.8.9 и owner publication до успеха разрешены текущей командой; IPA/device pending.

**Попытка182 прошла pre-SDK/cold gate и все прежние исправленные модули, затем дошла до основного TelegramUI:4ошибки в3файлах.** Новый `upstream_13_2_release_delivery_compile`:3замены/10guards. Добавлен TextFormat import; getStory разбирается как настоящий EngineStoryItem?, media как EngineMedia._asMedia(); ACK validation вынесена в типизированный helper с сохранением порядка/partial recipients; optional Contacts→Chats callback восстановлен для нашего root-tab, native Settings contacts по умолчанию прежние. Native source API/schema сверены напрямую.16fail-closed,6runtime исполнений debug/-O,4old story/contact compile errors и missing-import module boundary воспроизведены,4ACK semantic regressions отвергнуты. Полный source37641 имеет ровно3изменения; прежний source сохранён. Final47guards/423Swift parse/14PiP-R1-R2-R3 runtimes/native Postbox/strict71×629 повторно passed. Старый whole-module typecheck timeout воспроизводится только SDK182; изолированная проверка подтверждает новый typed loop, полныйSDKобязателен. Следующая чистая0.8.9 и owner publication до успеха разрешены; IPA/device pending.

**Попытка181: pre-SDK/cold gate прошли; ошибки179/180 не повторились. SDK остановился на3устаревших обращениях к анимации в одном PhoneEntry-файле.** Новый `upstream_13_2_release_auth_compile`:1точная замена/5guards; удалены visibility/managedAnimationNode вызовы для статичного ASImageNode, PNG и полная разметка сохранены.12fail-closed,2production visibility исполнения debug/-O и2отрицательных варианта с прежними member errors passed. Полный source37641: ровно1новое отличие, предыдущая композиция сохранена. Глобальные final SHA/47migration guards/native PostboxImportCheck иstrict71×629/44828lookup на режим повторно passed. Входы14ранее пройденных runtime-проверок не менялись; все mandatory CI checks сохранены перед новой чистой SDK-попыткой. Разрешение владельца на исправления/повторы0.8.9 до успешного IPA и owner publication подтверждено повторно. IPA/device пока pending.

**Попытка180: pre-SDK/cold gate прошли; прежние две compiler errors отсутствуют, SDK выявил3UI ошибки.** Новый `upstream_13_2_release_ui_compile`:3точные замены/6guards; объединена native agent-disposable и settings observer очистка в один deinit, crash export передаёт app bundleId с unconditional AppBundle import, spoiler gate получает текущие ContentSettings нового API13.2.16fail-closed,6production-boundary исполнений debug/-O и6 воспроизведений старых API ошибок прошли;32сочетания spoiler visibility на режим. Полный source37641 имеет только3ожидаемых отличия от предыдущей композиции, предыдущие стадии/шаблоны сохранены. Strict71×629 повторно passed. Далее новая чистая0.8.9 по действующему разрешению до успешной owner publication; IPA/device пока pending.

**Попытка179 прошла все pre-SDK проверки и cold gate, затем SDK выявил две ошибки компиляции.** Новый поздний `upstream_13_2_release_compile` исправляет только обращение к отсутствующему полю статичного intro и расположение Signal-error guard опроса. Все исторические snapshots и конечные outputs предыдущего post сохранены. Две точные замены/4guards;14fail-closed проверок, Clang-синтаксис реального VoiceOver-метода и Swift debug/-O границы upload прошли; прежние compiler errors воспроизведены отрицательными вариантами. Полное дерево37641: только2ожидаемых отличия, предыдущий полный source проверен. Strict71×629/44828lookup checks на режим повторно passed. Разрешение на исправление и повтор0.8.9 действует; следующая чистая SDK-попытка и owner publication до успеха, physical device pending.

**Попытка178 остановилась до SDK на final migration input guard; исправлена причина.** Все прежние проверки до final post прошли. Для AccountIntermediateState.swift был ошибочно выбран Before13.1.2 вместо неизменённого входа13.2; добавлен новый точный native snapshot,старый Before148.inc сохранён. Конечные274outputs и код функций не менялись. Полный реальный apply_overlay от чистой13.2 с legacy13.0,всеми историческими стадиями и обоими post теперь выполнен локально:37641файл,0 отличий от reviewed candidate;37289 исходных файлов pristine проверены.47fail-closed checks на настоящем результате повторно passed. Ранний CI gate сверяет7native git blobs и отвергает2регрессии происхождения до длинного набора тестов. Strict actual-source71×629/113files610calls passed. [Подробности](UPSTREAM_132_089_MIGRATION.md). Далее main commit/push и новая чистая0.8.9 по текущему разрешению; native SDK/IPA ещёpending.

**Попытка176: до SDK остановилась загрузка неопубликованного tgcalls gitlinkc1de0882.** Исправлен только checkout зависимости: официальный опубликованный38dcea12 закреплён SHA,все11прочих native refs прежние;проверены root pin/.gitmodules/gitlinks,6production digests и8negative/contract tests. Обязательная строка override включается в provenance и IPA gate; [подробности](UPSTREAM_132_089_MIGRATION.md). Exact fetch38dcea12 локально успешен. Следующая чистая попытка0.8.9 разрешена исходной командой;не спрашивать повторно.

## Предыдущий опубликованный выпуск0.8.8

**native_compile_passed / package_verified / owner_published / device_pending**

**0.8.8/build175 опубликован обычным latest релизом6 ноября2026 в12:16:54UTC.** [Релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.8), [IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.8.8/NagramiX-0.8.8-unsigned.ipa), [Actions](https://github.com/Mr-EFES/NagramiX/actions/runs/42197139124). Source2e01f89ca5c5d4a87d9d8f8e1bc267713bdf5650/main, tagv0.8.8 указывает на этот исходник. Все157pre-SDK проверки, cold gate, нативнаяARM64-компиляция10:46:47–12:12:53UTC, упаковка и независимаяCI проверкаIPA успешны. Автор релиза и uploader всех3файловMr-EFES; source/digest/размеры подтверждены. Compile passed/device pending.

IPA: 88449040байт, SHA256`8505ff723fabdc557475b8c9516d9a7028b536f50594b7c33c62207c80e92545`. Оригинальный Actions ZIP: artifact13500951945,88106901байт,SHA256`2155a638ed114283dd2a2b4ee9a89514f516b62107a7a02a809e0a077870b76e`; скачан через GitHub artifact tool, исходные байты сохранены в`/tmp/nagramix-build-088/original-actions-build175.zip` без перепаковки. FileServiceID file_000000000f1c821094a0b2a6ec941141. ПроверенныйIPA и3файла —`/tmp/nagramix-build-088/verified-build175/`. Проверка:0.8.8/build175/iOS15+/ARM64,6Mach-O/iPhoneOS,71×613 языков настроек/debug,RU15004/613,31мелодия,8иконок,без профилей,checksum/provenance. Символы175: artifact13500584303,SHA256`63b53ed053ce5d2f21ee2e276f26c67f64c823dffa31f3195473dcc29b150f43`,тот жеrun; символы173/174 не подменяют175.

Release436175279: normal/latest, authorMr-EFES. IPA asset717067980,provenance717067981,SHA256SUMS717067979; uploader каждогоMr-EFES, remote размер/digest совпали с локальным оригиналом. Тег2e01f89 проверен отдельно. Старые опубликованные0.8.4/0.8.5/0.8.7 и исторический пустой draft0.8.6/id435043558 не менялись.

Сохранённый личный CLI профиль`/workspace/.codex-nagramix-owner-gh` подтверждён какMr-EFES реальной загрузкой всех3release assets. Использовать env-uGH_TOKEN-uGITHUB_TOKEN; дляgit GIT_CONFIG_GLOBAL=/workspace/.codex-release-086/gitconfig. Несекретный selector`/workspace/.codex-release-088/owner-release-recovery.json`. Нового login не просить при действующей авторизации; credential-файлы не читать/выводить/коммитить.

Владелец6 ноября уточнил: личная команда выбирает новый выпуск и разрешает исправления причин сбоев с повторными чистыми попытками этого выпуска до успеха и owner publication; разрешение на каждый retry не спрашивать. Прежнее правило одной попытки заменено. Команда0.8.8 выполнена; следующий новый выпуск по умолчанию0.8.9 требует новой команды. Физическая приёмка на iPhone ещё не выполнена — [DEVICE_CHECK_088](DEVICE_CHECK_088.md). Пользователь вручную возвращает Make private после завершения; автоматически видимость не менять.

[Ошибка174 и исправление](RELEASE_088_DRAFT_UPLOAD_FIX.md) вошли в175. Первая174не создала IPA; чужой/старый173 не использован вместо нового175. Все5pending fixes с новыми copy/send tests вошли в релиз. Ниже история предыдущих выпусков; её старые статусы/разрешения не заменяют итог175 и уточнение владельца выше.

## История:0.8.7/build173 опубликован

Новая исходная правка [геометрии PiP](PIP_TRANSITION_GEOMETRY.md) добавлена после четырёх предыдущих pending исправлений. Source checks отдельно от Apple SDK/iPhone; новый compile_pending/device_pending. В IPA0.8.7/build173 этой правки нет, релиз/tag/assets не менялись. Новый SDK/Actions/IPA только по новой личной команде.

Новая исходная [правка пересылки/рассылки, заголовков и получателей из поиска](TRANSFER_CONSISTENCY.md) **не входит в опубликованную0.8.7/build173**. Обе copy-команды используют общий batch; данные новых получателей сохраняются до enqueue, заголовки соответствуют действию. Source checked/native_compile_pending/device_pending. Все предыдущие pending fixes сохранены; новый SDK/Actions/IPA/commit/push не запускался и требует отдельной личной команды.

Новая исходная [правка вложений расширенного редактора и карточек ссылок](EDITOR_ATTACHMENT_DELIVERY.md) **не входит в опубликованную0.8.7/build173**. Source checks пройдены; native_compile_pending/device_pending. Предыдущие fixes первого удаления и размеров моделей сохранены. Новые SDK/Actions/IPA/commit/push не запускались, на сборку нужна новая личная команда.

Новая исходная [правка размеров моделей](LOCAL_MODEL_SIZE.md) пока **не входит в опубликованную0.8.7/build173**: idle=размер, downloading=%, installed=без подписи/selectedcheckmark. Source checks пройдены, новаяSDK/device pending. Предыдущая анимация первого удаления сохранена; опубликованные IPA/tag не менялись.

Новая исходная [правка первого удаления](ARCHIVE_DELETION_EFFECT.md) ещё **не входит в этот опубликованный0.8.7/build173**. Source checks пройдены, native_compile_pending/device_pending; новых SDK/Actions/rerun/IPA/commit/push без отдельной команды не выполнялось. Текущие файлы и tag0.8.7 сохранены.

**native_compile_passed / package_verified / owner_published / device_pending**

**0.8.7/build173 опубликован обычным latest релизом5 ноября2026,20:19:04UTC.** [Release](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.7), [IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.8.7/NagramiX-0.8.7-unsigned.ipa), [Actions](https://github.com/Mr-EFES/NagramiX/actions/runs/42081412326). Source27217997bd5a691cfc2013b733e7be5646ed7479/main. Полный pre-SDK151 и cold gate успешны; нативная ARM64-компиляция19:10:47–20:15:25UTC, упаковка и независимый CI package job success. Оригинальный ZIP получен GitHub artifact tool после отказа CLI redirect, не перепакован: artifact13450251752,88094086bytes,SHA256d639b57e4a37fbc66631b8738fd229511bdadfc6ba2e09989edb9023c5038b09. IPA88438985bytes,SHA25642bd29773a4670a4d24083ae29cae789e38baccd68c76aa6567f8f6b10f9bc3d;0.8.7/build173/iOS15+/ARM64,71×613 языков настроек/debug, RU15004/613,31мелодия,8иконок, без профилей. Package validator локально и в owner publisher успешен; ZIP CI digest, checksum/provenance/source проверены. Release435547506, authorMr-EFES, uploader всех3файловMr-EFES, exact remote size/digest совпали; normal/latest, tagv0.8.7 указывает source2721799. Assets: IPA714687170, provenance714687171, SHA256SUMS714687169. Опубликованные старые релизы и исторический собственный пустой draft0.8.6/id435043558 не менялись.

Личный CLI profile `/workspace/.codex-nagramix-owner-gh` сохранён и доказан реальной загрузкой, повторный login не нужен при действующем профиле. Env-uGH_TOKEN-uGITHUB_TOKEN, git GIT_CONFIG_GLOBAL=/workspace/.codex-release-086/gitconfig; current non-secret selector `/workspace/.codex-release-087/owner-release-recovery.json`. Секреты не читать/выводить/коммитить. Текущая команда полностью выполнена; новый SDK/Actions/rerun только по новой личной команде. Все реализованные iOS compile_pending обновлены до compile_passed; physicaldevice_pending сохранён. [Проверка на iPhone](DEVICE_CHECK_087.md) ещё ожидается, UIKit/AVKit поведение физически не подтверждать. Владелец вручную закрывает repo через settings#danger-zone → Make private; не переключать автоматически.

## История0.8.6

# NagramiX0.8.6: попытка172 остановлена до SDK

Новая чистая [172](https://github.com/Mr-EFES/NagramiX/actions/runs/42078683279), sourceb0c60937cc793ed13c8363a606e00896099b3a1a, завершилась ошибкой17:54UTC5 ноября в первом новом тесте PiP. Swift/Xcode27.1 отклонил local weak var как never mutated при -warnings-as-errors. SDK не начинался, нового IPA и опубликованного релиза0.8.6 нет. Test-only исправление WeakGalleryProbe прошло85 checks/режим,13negative variants/режим,44fail-closed; post-port/import также проходят. Приложение/overlay не менялись. НовыйSwift/Xcode повторно не запускался, полная151 проверка ожидается вCI; локальный historical unwrap ограничен диском. ЕДИНСТВЕННЫЙ разрешённый запуск использован: следующая SDK попытка/Actions/rerun только по новой личной команде владельца. Draft435043558 и tag/assets не менялись.

# Историческая0.8.6/build171 — исправление PiP собрано и пакет проверен

По новой личной команде владельца готовится **новая чистая0.8.6 со всеми накопленными исправлениями**: temporary/copy/archive visibility/model menu и визуальный PiP. Локально прошли26 проверок, включая все новые стадии, и post-port/import. Остальной полный151 прогон остаётся обязательным в Actions до SDK; локальный historical unwrap упёрся в диск, не в assertion. Новая Actions готовится к запуску, нового IPA пока нет. Режим clean/publish=true, prerelease=false; owner authorization проверяется отдельно. Следующие сведения о171 остаются историческими и не описывают новый пакет.

Новая правка [PIP_VISUAL_HANDOFF](PIP_VISUAL_HANDOFF.md) согласует вход/возврат PiP, жесты, hidden-media и сохранение воспроизведения по двум утверждённым видео. **В IPA171 её нет**; новая SDK/device pending. Сборка/Actions/публикация этой задачи не запускались.

Правка [LOCAL_MODEL_MENU](LOCAL_MODEL_MENU.md) реализует утверждённые короткие названия Whisper/Vosk, проценты только до установки и native галочку выбранного ID. **В IPA171 её нет**; новая SDK/device pending, сборку этой задачи не запускали.


Правка [ARCHIVE_DELETION_VISIBILITY](ARCHIVE_DELETION_VISIBILITY.md) устраняет в исходниках скрытую ячейку сохранённого альбома после удаления оригинала. **В IPA171 её нет**; новая SDK/device pending. Ни сборку, ни Actions/rerun для этой задачи не запускали.


Последующая исходная правка [TEMPORARY_MEDIA_ACTIONS](TEMPORARY_MEDIA_ACTIONS.md) также **не входит в IPA171**: постоянная →A, кружки, архив после server deletion и обычные действия временных вложений. Новая SDK/device pending; Actions не запускались.


Последующая исходная правка [MESSAGE_COPY_AVAILABILITY](MESSAGE_COPY_AVAILABILITY.md) в этот IPA171 **не входит**; у неё compile_pending/device_pending. Следующая сборка только по отдельной личной команде владельца.

**native_compile_passed / package_verified / owner_publication_pending / device_pending**.

[Успешная сборка171](https://github.com/Mr-EFES/NagramiX/actions/runs/41991272414) · [Исходный ZIP с IPA](https://github.com/Mr-EFES/NagramiX/actions/runs/41991272414/artifacts/13405168153).

Оба задания Actions успешно завершились5 ноября2026,10:12:24UTC. Source `e07c143b174be87ebf7b77e920918c851a73beb0`, actor/triggering_actor Mr-EFES. Полный pre-SDK набор и cold gate прошли; чистая нативная компиляция без восстановления кеша завершена:9686 actions, SDK этап08:46:43–10:11:32UTC. База Telegram-iOS13.1.2, pin279f89e4d4f63f17227bf877dc3d8990f22ecd58, минимум iOS15.0. Позднейшие документы в main не меняют источник уже собранного IPA.

- IPA `NagramiX-0.8.6-unsigned.ipa`: **88424416 байт**, SHA256 `e0c5e93bf9dcb5f026376c981a58a4609947ba30c188b8df777c17d250a8cca3`.
- Оригинальный Actions ZIP: artifact13405168153, **88081499 байт**, SHA256 `e88ab08f39d435ee49765984202618dfc4c4bd2f21cc35b06eceea568df10a69`. Скачан без перепаковки, digest API совпал; CRC и ровно три плоских файла проверены.
- BUILD-PROVENANCE.txt:219байт, SHA256 `dcbca224302a4fac20641800550c32e8f1181997477c0c112c0ee8bab56641fd`.
- SHA256SUMS:94байт, SHA256 `549145831695afb420c3ad54b1e4e69536246b0d3301a16768915c096d16d853`.
- Независимый validate_unsigned_ipa подтвердил checksum/provenance/version/build/source,6 ARM64/iPhoneOS Mach-O, iOS15+,71 каталог по613 ключей настроек/debug,31 мелодию,8 иконок, отсутствие профилей/временных подписей.
- Символы новой171: artifact13406056676, ZIP166239668байт, SHA256 `ea36b824cb069e1d4556d22056c90b881a8ae5f09772a0f906771deabce4de5f`. Отдельное локальное сопоставление UUID новых символов не выполнялось.

## Публикация готового пакета ожидает входа владельца

Default runtime CLI подтверждает Mr-EFES для API, но uploads.github.com снова вернул401. Оставлен только собственный пустой draft435043558: authorMr-EFES, draft=true, tagv0.8.6, targete07c143b174be87ebf7b77e920918c851a73beb0. Файлов в нём нет, публичного релиза0.8.6 пока нет. Старый собственный пустой434878552 при PATCH target стал untagged; после проверки owner/empty/draft/source этот заменённый служебный черновик удалён. Опубликованные выпуски и assets не заменялись.

Официальный gh device flow запрошен заново, после проверки готового IPA. Owner profile /workspace/.codex-nagramix-owner-gh пока не подтверждён; коды/токены не сохраняются в Git. После входа проверить Mr-EFES и вызвать owner publisher с source-run41991272414 и исходным ZIP через env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR=<подтверждённый профиль>. Перед продолжением проверить состав draft: только свой пустой допускает обычный повтор; при частичной загрузке сначала сверить исходные digest/uploader и не перезаписывать файлы. Новый SDK запуск для публикации не нужен.

Устойчивый оригинальный ZIP171: `/workspace/.codex-release-086/original-actions.zip`; SHA выше. Recovery selector рядом указывает171, новый draft435043558 и неподтверждённый CLI profile. Старый170 ZIP сохранён только в task tmp для доказательств, запрещён к публикации.

## Причина падения170 и проверка устройства

Оба crash-отчёта170 символицированы по точному UUID IPA/dSYM `A616A3B2-D778-3FD2-87FC-A90312CF9BCF`: SourceAppearance.init:787 вызывает presentation() → QuartzCore → отсутствующий MediaPlayerNodeLayer.init(layer:) → SIGTRAP. Один стек пришёл через свайп, другой через кнопку. Удалены presentation lookup и отдельная cornerRadius-анимация sample-buffer слоя; оформление готовится без actions, переходом управляет AVKit.66 проверок/режим и6 отрицательных вариантов проходят; [полный контракт](PIP_FIRST_REQUEST.md).

170/run41971313591/source19bbb2b2a7f463315daa1fb4389a9605984206e9 публиковать нельзя. Её IPA SHA256 `b358b77b62450460902d19dd881a795df998a9d5a9550127e06af9fa1802f912`, ZIP artifact13394808694/SHA256 `fa5e1e8561aa4580178bde7d42f08cac1979dc9f9e13c30f839da2a1cd25949a`. Символы170 artifact13394818659/SHA256 `1530f9ce03e1e6565e06b689f423ac031a96333d19594ed601aa5d6f42e63788` совпали по UUID с обоими отчётами.

Повторная физическая проверка PiP171 по кнопке/свайпу и плавности на iPhone **ожидается**: [сценарии0.8.6](DEVICE_CHECK_086.md). Новые сборки и rerun только по отдельной личной команде владельца; текущую171 он отдельно разрешил продолжать, она завершена. После завершения публикации напомнить владельцу ручной Make private; видимость автоматически не менять.

## Опубликованная сборка0.8.5/build165

**Обычный релиз 0.8.5/build165 опубликован. Нативная компиляция и проверка скачанного release IPA пройдены. Физическая проверка на iPhone ожидается.**

[Успешная сборка, попытка 2](https://github.com/Mr-EFES/NagramiX/actions/runs/41734603786/attempts/2) · [Исходный ZIP с IPA и метаданными](https://github.com/Mr-EFES/NagramiX/actions/runs/41734603786/artifacts/13288720208) · [Релиз 0.8.5](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.5) · [Скачать IPA](https://github.com/Mr-EFES/NagramiX/releases/download/v0.8.5/NagramiX-0.8.5-unsigned.ipa).

База Telegram-iOS **13.1.2**, commit `279f89e4d4f63f17227bf877dc3d8990f22ecd58`, минимум iOS15.0. Оба задания Actions завершены успешно 4 ноября 2026 года. Actor и triggering_actor — Mr-EFES. Режим clean_build/publish_release включён; восстановление кеша отключено, cold gate пройден.

## Проверенный пакет

- IPA: `NagramiX-0.8.5-unsigned.ipa`, **86539866 байт**.
- SHA256 IPA: `1386cf0a4610a50fd4d32de2061a056fc2ed3277fc8acd2f4e571fbd0e4041bb`.
- Исходник бинарного пакета: `a75ab958d67c6b0aea0ef214e27175da9ace8358`. Дальнейшие правки публикации и документации в main не меняют этот provenance.
- Оригинальный Actions ZIP: artifact **13288720208**, **86268157 байт**, SHA256 `cc3c009e8d6c24bc10ada00179d9996e1bcf607f0053d203cdc545d85a6b8006`. Получен через GitHub artifact tool, скачан без перепаковки и сопоставлен с digest API.
- В ZIP ровно три файла: IPA, `BUILD-PROVENANCE.txt`, `SHA256SUMS`. Локально подтверждены CRC, checksum, версия/build/источник, 6 ARM64/iPhoneOS Mach-O с iOS15+, отсутствие временных подписей и профилей, RU/EN, 31 мелодия и 8 иконок.
- Символы: Actions artifact `NagramiX-0.8.5-symbols-arm64`, ID **13287751850**. Отдельное локальное сопоставление UUID dSYM не выполнялось.

Статус: **native_compile_passed / package_verified / release_published_verified / device_pending**. Подпись для установки выполняется отдельно. Физические сценарии — [проверка 0.8.5 на iPhone](DEVICE_CHECK_085.md).

## Подтверждённая публикация

Релиз **433416662** опубликован **4 ноября 2026, 06:21:29 UTC**, draft=false, prerelease=false, latest. Автор и uploader каждого файла — **Mr-EFES**. Тег `v0.8.5` указывает commit `a75ab958d67c6b0aea0ef214e27175da9ace8358`, из которого собран IPA; последующие изменения main относятся к публикации и документации. Body содержит только утверждённое описание приложения.

| Файл | Asset ID | Байт | SHA256 |
| --- | --- | --- | --- |
| BUILD-PROVENANCE.txt | 708473521 | 219 | `7b75a7480e8ae1cc5ba45fea60e97100a5b67c8dcc6561db259d6d23c862f46e` |
| NagramiX-0.8.5-unsigned.ipa | 708473519 | 86539866 | `1386cf0a4610a50fd4d32de2061a056fc2ed3277fc8acd2f4e571fbd0e4041bb` |
| SHA256SUMS | 708473528 | 94 | `8b336e0c5c5a8aff26cc413c240d98bce596c8510065106038e2a35d5b1d9517` |

Все три файла повторно скачаны из опубликованного релиза. Их состав, размеры и digest совпали с исходным Actions ZIP; validate_unsigned_ipa повторно подтвердил версию/build/source, CRC/checksum/provenance, платформу и ресурсы. Проверены latest, источник тега, автор и uploader каждого файла. Повторно запускать publisher для этого опубликованного релиза нельзя: его замена запрещена.

Предыдущий HTTP401 uploads.github.com устранён официальным повторным входом GitHub CLI, подтверждённым владельцем через сайт GitHub. Исходный runtime GH_TOKEN работал для API, но отклонялся сервером загрузки. Для команды публикации выбран подтверждённый профиль CLI без приоритетного GH_TOKEN; общая среда и её credentials не менялись. Токены не запрашивались в чат, не извлекались и не коммитились. Пересборка приложения для этого не выполнялась. Порядок выбора профиля и защиты от замены файлов — [RELEASE_VERSIONING](RELEASE_VERSIONING.md).

## Сохранённый опубликованный 0.8.4

Релиз/tag/IPA **0.8.4/build162** сохранены: [релиз](https://github.com/Mr-EFES/NagramiX/releases/tag/v0.8.4), [успешная сборка](https://github.com/Mr-EFES/NagramiX/actions/runs/41355923502). Размер IPA **86523244 байта**, SHA256 `bf9bc20d42a130c2f211210636cab6f523882201df56be335581f57202d2efe4`. Его исходный provenance — `9d66a823b8b8af2bcaf663f9b9ead9db47843123`; свёрнутый корневой commit/tag `fd14548b7517c1619db44c9a1f6bbb9a55b48b9c` не подменяет исходник уже собранного пакета. Оригинальный ZIP: 86252784 байта, SHA256 `e87fe90aefdfbef8f0ac2c2363707472828f64e76f6c736707aec5da513c96e5`. Исторический автор/uploaders github-actions[bot] не менялись; старые assets не заменяются.

После публикации GitHub API подтвердил видимость **private**. Репозиторий закрыт; ручной [порядок переключения](REPOSITORY_VISIBILITY.md) сохраняется для следующих сборок.
