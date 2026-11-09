"""Явное согласие на открытие временного медиа и сохранение локального содержимого."""
import hashlib
import json
from pathlib import Path


def apply_content_interaction_consent(source: Path, overlay: Path) -> None:
    plan = json.loads((overlay / 'content_interaction_consent_patches.json').read_text())
    expected_inputs = set(['submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift', 'submodules/TelegramCore/Sources/State/ManagedSynchronizeConsumeMessageContentsOperations.swift', 'submodules/TelegramCore/Sources/State/ManagedSecretChatOutgoingOperations.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/TelegramEngineMessages.swift', 'submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift', 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift', 'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/af.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sq.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/am.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ar.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hy.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/az.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/eu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/be.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/bn.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/bg.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/my.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ca.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/zh-hans.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/zh-hant.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/cs.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/da.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/nl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/eo.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/et.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fil.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/gl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ka.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/de.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/el.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/gu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/he.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hi.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/hu.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/id.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ga.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/it.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ja.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/kn.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/kk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/km.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ko.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/lv.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/lt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ms.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ml.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/mt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/mr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ne.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/nb.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/or.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/fa.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pt-br.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/pt-pt.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ro.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sl.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/es.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sw.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/sv.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/tg.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ta.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/te.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/th.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/tr.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/tk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/uk.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/ur.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/uz.lproj/Localizable.strings', 'submodules/NagramiXCore/Resources/vi.lproj/Localizable.strings', 'submodules/TelegramCore/Sources/State/SynchronizeConsumeMessageContentsOperation.swift', 'submodules/TelegramCore/Sources/SecretChats/SetSecretChatMessageAutoremoveTimeoutInteractively.swift'])
    required_guards = set(['submodules/TelegramCore/Sources/Utils/NagramiXArchivePersistence.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXArchivedMediaStore.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXContentCopy.swift', 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift', 'submodules/TelegramCore/Sources/TelegramEngine/Messages/ApplyMaxReadIndexInteractively.swift', 'submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift', 'submodules/TelegramCore/Sources/ApiUtils/StoreMessage_Telegram.swift', 'submodules/TelegramCore/Sources/State/Sync/StateReplay+Messages.swift', 'submodules/TelegramCore/BUILD', 'submodules/TelegramUI/BUILD', 'submodules/NagramiXCore/BUILD', 'submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift', 'submodules/TelegramUI/Sources/ChatHistoryEntriesForView.swift', 'submodules/NagramiXMediaSettings/Sources/NagramiXMediaSettings.swift', 'submodules/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift', 'submodules/Display/Source/NagramiXCaptureProtection.swift', 'submodules/TelegramCore/Sources/Settings/ContentSettings.swift', 'submodules/TelegramCore/Sources/Utils/PeerUtils.swift', 'submodules/PlatformRestrictionMatching/Sources/PlatformRestrictionMatching.swift', 'submodules/GalleryUI/Sources/NagramiXGallerySavePolicy.swift', 'submodules/TelegramUI/Sources/ChatController.swift', 'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift'])
    if (plan['target_pin'] != '24638bc69bd083981b178dd1e7f921eebbf7fc46'
        or plan['overlay_base_pin'] != '279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage') != 'hide_premium_offers'
        or set(plan['inputs']) != expected_inputs
        or any(plan['inputs'].keys() != plan[field].keys() for field in ('outputs', 'previous', 'replacements'))
        or set(plan['inputs']) & set(plan['guards'])
        or plan['copies'] or plan['deletions']
        or not required_guards <= plan['guards'].keys()
        or set(plan['guard_sources']) != set(plan['guards'])
        or not set(plan.get('native_inputs', {})) <= set(plan['inputs'])):
        raise SystemExit('content_interaction_consent: inconsistent manifest')

    def safe(root: Path, name: str) -> Path:
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('content_interaction_consent: unsafe path ' + name)
        if path.is_symlink():
            raise SystemExit('content_interaction_consent: symlink ' + name)
        return path

    def checked(root: Path, name: str, expected: str) -> bytes:
        path = safe(root, name)
        if not path.is_file():
            raise SystemExit('content_interaction_consent: missing ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('content_interaction_consent: drift ' + name)
        return data

    def template(name: str, expected: str) -> bytes:
        if plan['templates'].get(name) != expected:
            raise SystemExit('content_interaction_consent: unregistered template ' + name)
        return checked(overlay, name, expected)

    for name, expected in plan['templates'].items():
        checked(overlay, name, expected)
    for name, expected in plan['guards'].items():
        if checked(source, name, expected) != template(plan['guard_sources'][name], expected):
            raise SystemExit('content_interaction_consent: guard mismatch ' + name)
    prepared = {}
    for name, expected in plan['inputs'].items():
        before = template(plan['previous'][name], expected)
        if checked(source, name, expected) != before:
            raise SystemExit('content_interaction_consent: previous mismatch ' + name)
        if name in plan.get('native_inputs', {}):
            blob = hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest()
            if blob != plan['native_inputs'][name]:
                raise SystemExit('content_interaction_consent: native input origin ' + name)
        prepared[name] = template(plan['replacements'][name], plan['outputs'][name])
    # Validate every preimage, dependency and destination before writing source.
    for name, data in prepared.items():
        safe(source, name).write_bytes(data)
