# Текущий контекст NagramiX 0.5.0

## Задача завершена: чистая сборка №83 и новый IPA проверены

Пользователь 2026-10-10 разрешил новую сборку 0.5.0 для физического теста. Сохраняется ранее согласованный процесс тестовой публикации: единственный build-unsigned-ipa.yml на main, artifact_run_id пустой, clean_build=true, publish_release=true, prerelease=true. Новое согласование на уже разрешённые push/build/release не нужно. Старые релизы/теги/IPA сохранять. Источник должен быть новым commit со всеми накопленными правками, прежний пакет не переиздавать.

База Telegram13.0 / f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838 повторно CURRENT. Минимум iOS15.0, ARM64 unsigned, bundle com.mr-efes.nagramix. Linux без Xcode: build только macOS workflow. Credentials не выводить и не коммитить. Номер build=GITHUB_RUN_NUMBER.

Версия workflow/README/AGENTS/LICENSE/gitignore/product registry/releases и план iPhone обновлены согласованно. Только текущая аннотация product/releases/0.5.0.md, русский функциональный текст. docs/RELEASE_STATUS.md фиксирует успешную сборку и независимую проверку нового IPA. Все реализованные записи registry имеют compile_passed/device_pending; физическую приёмку не объявлять.

## Состав и ограничения новых изменений

1. Звуки: apply_notification_sound_catalog,31 M4A (23 системные +8 классических), local native ID/file mapping независимо от cloud cache; hash0 refresh, custom upload сохранён, NotificationService local fallback. manifest/source/hashes, tests/test_notification_sound_resources.py и validator IPA. [Контракт](NOTIFICATION_SOUNDS_FIX.md).
2. QR: apply_qr_brightness_restore, snapshot/restore idempotent до share/close/dismiss/background/deinit, weak callbacks, no late reboost; stock UI/links/proxy types. [Контракт](PROXY_QR_BRIGHTNESS_FIX.md).
3. Инкогнито: NagramiXStorySettings Foundation-only в existing media module, absentOFF/savedvalues, key nagramix.stories.anonymousViewing, IDs123–124. Фиксированная политика четырёх native contexts, engine gates до read queue/maxId/counter, eye.slash и предупреждение перед reply/reaction. Protected approval/cancel/confirmation не изменять. Whole-blob/5 integrated UI SHA guards require deliberate audit. Это только будущие client views, не Premium5/25, не стирание старых просмотров и не обещание анонимности после обычной новой истории/другого клиента/ответа. [Контракт и два аккаунта](../product/features/story-incognito.md).
4. Ускорение: только .medium/.maximum, native ActionSheetCheckboxItem(style:.alignRight), left label/right tick, checkbox only ON/OFF. Legacy raw0 нормализуетсяmedium, malformed безопасныйOFF; сохранённыйOFF остаётсяOFF. Keys/raw1/2 и limits12/1MiB/6workers,24/8 unchanged. [Контракт](../product/features/download-acceleration.md).
5. Навигация: apply_separate_profile_navigation_buttons, общий PeerInfoHeaderNavigationButtonContainerNode, смешанные правые группы с текстом — отдельные native GlassContextExtractableContainer/gap8; icon-only stock. Creation/cached layout/reparent coordinates/alpha/removal/tint/context/hit gaps. Полные labels/fonts untouched. Whole Git blob ffe35bf77b9099b5fa835a11e2c7a3327594fcb3. [Охват аудита и план](PROFILE_NAVIGATION_LAYOUT_FIX.md).

## Предварительные проверки

Полный feature overlay на350 SHA-verified raw blobs /tmp/nagramix-navigation-full-raw, proof /tmp/nagramix-navigation-full-proof. Последняя навигационная правка: один native файл изменён,410 остальных равны и все410 prior pending файлов сохранены. Swift grammar passed,6 substitutions/19 drift cases без мутаций,280 measured-width geometry cases (не реальные UIKit/fonts/avatar). Остальные pending guarded patches проверены в предыдущих targeted harnesses; история их изменений и проверок в Git. Нельзя ослаблять exact anchors ради успешной сборки.

До push: Python/metadata/intro RU/diff, tests31audio, полный overlay и syntax; проверить staged paths на секреты/временные деревья. Commit с русским сообщением, normal push main. Dispatch нового clean run, проверить head_sha и actual inputs. При native ошибке исправлять её узко, повторять чистую сборку с новым commit; не публиковать старый пакет.

После success: скачать IPA/BUILD-PROVENANCE.txt/SHA256SUMS именно из нового релиза. validate_unsigned_ipa.py с фактическими version/build/source/run, ZIP CRC, SHA256, bundle/minOS/audio/RU/31tones/ARM64/unsigned; tag==source,release body==tracked file, prerelease. Обновить registry compile status и результат RELEASE_STATUS/README/AGENTS/handoff; documentation checkpoint не выдавать за собранный source.

## Защищённые прежние функции

Сохранять камеру кружков сзади, per-story confirmation/approval/cancel/seen gate, запрет camera swipe/скрытие/repost историй, ID/дата/контакты, wide posts/mosaics, скрытиеContacts/Calls, Proxy/sponsor. Темы/шрифты stock с уже согласованными точечными совместимостями. Defaults/keys/IDs/ручные предпочтения не сбрасывать.

Меню chatsON: folder pans везде, hold неavatar stock actionsArchive/Unarchive; avatar tap/hold в обоих режимах полноэкранный отдельный readonly chat без read/input. ForwardWithout single native destination draft/quiet/schedule; Broadcast multi; deleted snapshots copy native, не server forward deletedID, подпись автора не согласована. Архив: независимое хранениеполученных файлов/TTL optin, late callbacks/clear guards, alpha0.5, штатный shared decoder одного полного MessageId/fileId/resourceId без второго moving renderer. JPEG progressive contract/quality0–100/native legacy72/full-cache decode and heap errors; фон decoder UUID ownersORnativePiP. Не упрощать эти пути.

## Подтверждённый результат и следующий шаг

Чистая сборка №83/run38036214917/source132ddc364706d63cc31746be343627419c36c85f прошла успешно, 7696 actions; cache restore/save оба skipped. Новый тестовый релиз v0.5.0 опубликован 2026-10-10T09:16:49Z; tag==source, body==tracked functional RU annotation, non-draft/prerelease. Независимо проверены новые IPA/provenance/checksum/ZIP CRC, version/build/source/run,6ARM64 iOSMachO, no profiles/_CodeSignature,46полныхRUlabels,14863основныхRU/224customRU и EN keys,31tones SHA256,minimumiOS15/audio mode. IPA 80822420bytes, SHA2562f2df666b71b078cf26c6fb8811657424b4e19c7d7c77de70eca9bf0e213347b. /tmp/nagramix-release-050/VERIFIED-RELEASE.json и build.log; отчёт docs/RELEASE_STATUS.md.

Прямой IPA: https://github.com/Mr-EFES/NagramiX/releases/download/v0.5.0/NagramiX-0.5.0-unsigned.ipa
Релиз: https://github.com/Mr-EFES/NagramiX/releases/tag/v0.5.0
Пакет unsigned требует внешней подписи SideStore. Шесть LC_CODE_SIGNATURE load records не дают установочную подпись. Новый пакет не является прежним переизданным IPA. Последующий documentation checkpoint не менять/не выдавать за собранный source132ddc3.

Следующий шаг — физический тест пользователя по docs/IPHONE_TEST_0.5.0.md и пяти текущим контрактам. Инкогнито проверить двумя аккаунтами; реальный UI/яркость/звук/network/playback/crash-free не объявлять проверенными. Новые правки в следующей сборке только по новой команде пользователя; новые релизы не запускать автоматически. Все прежние releases/tags/history сохранить.
