#!/usr/bin/env python3
"""Проверить ввод личных ключей и обновление моделей без Apple SDK и реальных секретов."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
SPEECH = 'submodules/NagramiXTranscription/Sources/'
TRANSLATION = 'submodules/TranslateUI/Sources/'
PLAN = json.loads((OVERLAY / 'cloud_credential_entry_patches.json').read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source):
    for name, value in {**PLAN['outputs'], **PLAN['guards']}.items():
        assert sha((source / name).read_bytes()) == value, name
    for name, value in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == value, name
    for name, template in PLAN['previous'].items():
        assert sha((OVERLAY / template).read_bytes()) == PLAN['inputs'][name], name
    for name, template in PLAN['replacements'].items():
        assert sha((OVERLAY / template).read_bytes()) == PLAN['outputs'][name], name


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('cloud_credential_entry', OVERLAY / 'cloud_credential_entry.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = {n: (OVERLAY / t).read_bytes() for n, t in PLAN['previous'].items()}
    dependencies = {n: (source / n).read_bytes() for n in PLAN['guards']}
    count = 0

    def seed():
        dest = temp / 'seed'
        if dest.exists():
            shutil.rmtree(dest)
        for n, data in {**before, **dependencies}.items():
            p = dest / n
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        return dest

    def reject(dest, label, overlay=OVERLAY):
        nonlocal count
        previous = manifest(dest)
        try:
            module.apply_cloud_credential_entry(dest, overlay)
        except SystemExit:
            pass
        else:
            raise AssertionError('Accepted invalid state: ' + label)
        assert previous == manifest(dest), 'Partial writes: ' + label
        count += 1

    dest = seed()
    module.apply_cloud_credential_entry(dest, OVERLAY)
    verify(dest)
    reject(dest, 'repeat')
    for n in {**before, **dependencies}:
        for mode in ['missing', 'drift']:
            dest = seed()
            p = dest / n
            if mode == 'missing':
                p.unlink()
            else:
                p.write_bytes(p.read_bytes() + b'\ndrift')
            reject(dest, mode + ' ' + n)
    altered = temp / 'overlay'
    for n in PLAN['templates']:
        p = altered / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((OVERLAY / n).read_bytes())
    for mode in ['template', 'pin', 'unsafe', 'manifest']:
        plan = copy.deepcopy(PLAN)
        if mode == 'pin':
            plan['target_pin'] = 'unreviewed'
        elif mode == 'unsafe':
            plan['templates']['../escape'] = '0' * 64
        elif mode == 'manifest':
            plan['outputs'].pop(next(iter(plan['outputs'])))
        else:
            n = next(iter(plan['templates']))
            (altered / n).write_bytes(b'changed')
        (altered / 'cloud_credential_entry_patches.json').write_text(json.dumps(plan))
        reject(seed(), mode, altered)
        for n in PLAN['templates']:
            (altered / n).write_bytes((OVERLAY / n).read_bytes())
    return count


BOUNDARIES = r'''
import Foundation

// Defaults and Security.framework are explicit in-memory boundaries. Only synthetic
// fixture tokens are used. Actual production Settings/Credentials bodies execute.
final class CredentialTestDefaults {
    static let shared = CredentialTestDefaults()
    var items: [String: Any] = [:]
    func object(forKey key: String) -> Any? { self.items[key] }
    func data(forKey key: String) -> Data? { self.items[key] as? Data }
    func set(_ value: Any?, forKey key: String) { self.items[key] = value }
}

private var checks = 0
private func check(_ value: @autoclosure () -> Bool, _ label: String) {
    checks += 1
    if !value() { FileHandle.standardError.write(Data(("FAIL " + label + "\n").utf8)); exit(91) }
}

final class DraftField { var text: String? }
final class DraftLabel { var text: String? }
final class DraftCell { let detailTextLabel: DraftLabel? = DraftLabel() }
final class DraftTable {
    var cells: [IndexPath: DraftCell] = [:]
    func cellForRow(at path: IndexPath) -> DraftCell? {
        if let cell = self.cells[path] { return cell }
        let cell = DraftCell(); self.cells[path] = cell; return cell
    }
    func reloadData() {}
}
extension IndexPath { init(row: Int, section: Int) { self.init(indexes: [section, row]) } }
struct DraftStrings { func nagramiXUILocalized(_ value: String) -> String { value } }
struct DraftPresentationData { let strings = DraftStrings() }
final class DraftView { var window: Bool? = true }

// Same request/completion signature as the guarded catalog implementation.
// HTTP and frame/layout presentation are the boundary; no live request occurs.
// ERROR_ENUM

enum NagramiXRemoteModelCatalog {
    struct Request {
        let provider: String
        let speech: Bool
        let key: String
        let account: String
        let completion: (Result<[String], NagramiXRemoteCatalogError>) -> Void
    }
    static var requests: [Request] = []
    static func fetch(provider: String, speech: Bool, key: String, account: String = "", completion: @escaping (Result<[String], NagramiXRemoteCatalogError>) -> Void) {
        requests.append(Request(provider: provider, speech: speech, key: key, account: account, completion: completion))
    }
    static func message(_ error: NagramiXRemoteCatalogError) -> String { String(describing: error) }
    static func complete(_ index: Int, _ result: Result<[String], NagramiXRemoteCatalogError>) {
        requests[index].completion(result)
        _ = RunLoop.current.run(mode: .default, before: Date(timeIntervalSinceNow: 0.01))
    }
}
final class NagramiXTranscriptionModelPicker {
    let models: [String]
    let completion: (String) -> Void
    init(models: [String], selected: String, presentationData: DraftPresentationData, completion: @escaping (String) -> Void) {
        self.models = models; self.completion = completion
    }
}
final class NagramiXTranslationModelPicker {
    let models: [String]
    let completion: (String) -> Void
    init(models: [String], selected: String, presentationData: DraftPresentationData, completion: @escaping (String) -> Void) {
        self.models = models; self.completion = completion
    }
}
'''


CREDENTIAL_TESTS = r'''
private func fresh() {
    CredentialTestDefaults.shared.items = [:]
    KeychainBoundary.items = [:]
    KeychainBoundary.denied = false
}
private func marker(_ speech: Bool, _ provider: String) -> String {
    "nagramix." + (speech ? "transcription" : "translation") + ".credential.userEntry.v1." + provider
}
private func credentialTests() {
    let bundle = Bundle.main.bundleIdentifier ?? "NagramiX"
    let speechService = bundle + ".transcription.keys:"
    let translationService = bundle + ".translation.keys:"
    for provider in NagramiXTranscriptionProvider.allCases.filter({ $0.cloud }) {
        fresh()
        KeychainBoundary.items[speechService + provider.rawValue] = Data("retained-from-previous-install".utf8)
        NagramiXTranscriptionSettings.update { $0.provider = provider }
        check(NagramiXTranscriptionKeys.read(provider) == nil, "fresh retained ASR key ignored")
        check(CredentialTestDefaults.shared.object(forKey: marker(true, provider.rawValue)) as? Bool == false, "fresh ASR proof false")
        NagramiXTranscriptionSettings.update { $0.models[provider.rawValue] = provider.defaultModel; $0.credentialRevision = "later-setting" }
        check(NagramiXTranscriptionKeys.read(provider) == nil, "false ASR proof cannot become implicit import")
        let revision = NagramiXTranscriptionSettings.current.credentialRevision
        check(NagramiXTranscriptionKeys.save("user-new-entry", provider: provider), "ASR explicit save")
        check(NagramiXTranscriptionKeys.read(provider) == "user-new-entry", "ASR exact new key")
        check(NagramiXTranscriptionSettings.current.credentialRevision != revision, "ASR save invalidates old work")
        check(KeychainBoundary.lastQuery[kSecAttrService] as? String == bundle + ".transcription.keys", "ASR service isolated")
        check(KeychainBoundary.lastQuery[kSecAttrSynchronizable] as? Bool == false, "ASR never syncs")
        check(CredentialTestDefaults.shared.object(forKey: marker(true, provider.rawValue)) as? Bool == true, "ASR entry proof persists")
        KeychainBoundary.denied = true
        check(!NagramiXTranscriptionKeys.save("failed-new-key", provider: provider), "ASR failed update")
        check(!NagramiXTranscriptionKeys.save(nil, provider: provider), "ASR failed deletion")
        check(CredentialTestDefaults.shared.object(forKey: marker(true, provider.rawValue)) as? Bool == true, "ASR failed operation keeps ownership")
        KeychainBoundary.denied = false
        check(NagramiXTranscriptionKeys.read(provider) == "user-new-entry", "ASR denied operations preserve own key")
        check(!NagramiXTranscriptionKeys.save("header\r\ninjection", provider: provider), "ASR control character rejected")
        check(NagramiXTranscriptionKeys.save(nil, provider: provider), "ASR clear")
        KeychainBoundary.items[speechService + provider.rawValue] = Data("retained-again".utf8)
        check(NagramiXTranscriptionKeys.read(provider) == nil, "ASR clear cannot revive retained key")
        check(CredentialTestDefaults.shared.object(forKey: marker(true, provider.rawValue)) as? Bool == false, "ASR clear proof false")
        fresh()
        KeychainBoundary.items[speechService + provider.rawValue] = Data("legitimate-upgrade-key".utf8)
        NagramiXTranscriptionSettings.update { $0.models[provider.rawValue] = provider.defaultModel; $0.credentialRevision = "saved-before-upgrade" }
        check(NagramiXTranscriptionKeys.read(provider) == "legitimate-upgrade-key", "ASR legitimate upgrade preserved")
        check(NagramiXTranscriptionKeys.read(provider) == "legitimate-upgrade-key", "ASR upgrade stable")
        fresh()
        KeychainBoundary.items[speechService + provider.rawValue] = Data("unowned".utf8)
        KeychainBoundary.denied = true
        check(!NagramiXTranscriptionKeys.save("not-saved", provider: provider), "ASR denied fresh save")
        KeychainBoundary.denied = false
        check(NagramiXTranscriptionKeys.read(provider) == nil, "failed ASR save does not establish proof")
    }
    for provider in NagramiXTranslationProvider.allCases.filter({ $0.requiresAPIKey }) {
        fresh()
        KeychainBoundary.items[translationService + provider.rawValue] = try! JSONEncoder().encode(NagramiXTranslationCredential(key: "retained-from-previous-install", folder: ""))
        NagramiXTranslationSettings.update { $0.provider = provider }
        check(NagramiXTranslationKeys.read(provider) == nil, "fresh retained translation key ignored")
        check(CredentialTestDefaults.shared.object(forKey: marker(false, provider.rawValue)) as? Bool == false, "fresh translation proof false")
        NagramiXTranslationSettings.update { $0.models[provider.rawValue] = provider.defaultModel }
        check(NagramiXTranslationKeys.read(provider) == nil, "false translation proof cannot become implicit import")
        let revision = NagramiXTranslationSettings.current.revision
        check(NagramiXTranslationKeys.save(.init(key: "user-new-entry", folder: ""), provider: provider), "translation explicit save")
        check(NagramiXTranslationKeys.read(provider)?.key == "user-new-entry", "translation exact new key")
        check(NagramiXTranslationSettings.current.revision != revision, "translation invalidates old work")
        check(KeychainBoundary.lastQuery[kSecAttrService] as? String == bundle + ".translation.keys", "translation service isolated")
        check(KeychainBoundary.lastQuery[kSecAttrSynchronizable] as? Bool == false, "translation never syncs")
        KeychainBoundary.denied = true
        check(!NagramiXTranslationKeys.save(.init(key: "failed", folder: ""), provider: provider), "translation failed update")
        check(!NagramiXTranslationKeys.save(nil, provider: provider), "translation failed deletion")
        KeychainBoundary.denied = false
        check(NagramiXTranslationKeys.read(provider)?.key == "user-new-entry", "translation failed operation preserves key")
        check(NagramiXTranslationKeys.save(nil, provider: provider), "translation clear")
        KeychainBoundary.items[translationService + provider.rawValue] = try! JSONEncoder().encode(NagramiXTranslationCredential(key: "retained-again", folder: ""))
        check(NagramiXTranslationKeys.read(provider) == nil, "translation clear cannot revive retained key")
        fresh()
        KeychainBoundary.items[translationService + provider.rawValue] = try! JSONEncoder().encode(NagramiXTranslationCredential(key: "legitimate-upgrade-key", folder: ""))
        NagramiXTranslationSettings.update { $0.models[provider.rawValue] = provider.defaultModel }
        check(NagramiXTranslationKeys.read(provider)?.key == "legitimate-upgrade-key", "translation legitimate upgrade preserved")
        check(NagramiXTranslationKeys.read(provider)?.key == "legitimate-upgrade-key", "translation upgrade stable")
    }
    fresh()
    check(NagramiXTranscriptionKeys.read(.apple) == nil, "Apple no key")
    check(NagramiXTranscriptionKeys.read(.whisper) == nil, "Whisper no key")
    check(NagramiXTranslationKeys.read(.google) == nil, "Google no API key")
    check(NagramiXTranscriptionKeys.save("speech-own", provider: .gemini), "save separate ASR")
    check(NagramiXTranslationKeys.save(.init(key: "translate-own", folder: ""), provider: .gemini), "save separate translation")
    check(NagramiXTranscriptionKeys.read(.gemini) == "speech-own", "ASR never borrows translation")
    check(NagramiXTranslationKeys.read(.gemini)?.key == "translate-own", "translation never borrows ASR")
    let defaults = CredentialTestDefaults.shared.items.values.map { String(describing: $0) }.joined()
    check(!defaults.contains("speech-own") && !defaults.contains("translate-own"), "only Boolean proof in Defaults")
    // Simulated reinstall: Keychain remains; app preferences and proof disappear.
    CredentialTestDefaults.shared.items = [:]
    check(NagramiXTranscriptionKeys.read(.gemini) == nil, "ASR reinstall starts empty")
    check(NagramiXTranslationKeys.read(.gemini) == nil, "translation reinstall starts empty")
}
'''


UI_TESTS = r'''
private func speechCatalogTests() {
    for provider in NagramiXTranscriptionProvider.allCases.filter({ $0.cloud }) {
        NagramiXRemoteModelCatalog.requests = []
        let ui = SpeechCredentialUI()
        ui.page = .credential(provider)
        ui.selectedModel = provider.defaultModel
        ui.loadCatalog(provider, openPicker: false)
        check(NagramiXRemoteModelCatalog.requests.isEmpty, "empty ASR draft no request")
        ui.loadCatalog(provider, openPicker: true)
        check(ui.alerts == ["missingKey"], "empty ASR picker requests key")
        check(NagramiXRemoteModelCatalog.requests.isEmpty, "empty ASR picker no request")
        ui.keyField.text = " first-key "
        ui.accountField.text = "01234567890123456789012345678901"
        ui.credentialEdited()
        ui.credentialEditingEnded()
        check(NagramiXRemoteModelCatalog.requests.count == 1, "ASR end edit loads catalog")
        check(NagramiXRemoteModelCatalog.requests[0].provider == provider.rawValue && NagramiXRemoteModelCatalog.requests[0].speech, "ASR exact provider")
        check(NagramiXRemoteModelCatalog.requests[0].key == "first-key", "ASR exact current draft")
        check(ui.catalogLoading, "ASR loading true")
        ui.loadCatalog(provider, openPicker: true)
        check(NagramiXRemoteModelCatalog.requests.count == 1 && ui.catalogWantsPicker, "ASR pending picker coalesces")
        NagramiXRemoteModelCatalog.complete(0, .success(["available-one", "available-two"]))
        check(!ui.catalogLoading && ui.catalogModels == ["available-one", "available-two"], "ASR models arrive")
        check(ui.pickers.count == 1, "ASR picker opens after request")
        ui.pickers[0].completion("available-two")
        check(ui.selectedModel == "available-two", "ASR current catalog selection")
        ui.loadCatalog(provider, openPicker: true)
        check(NagramiXRemoteModelCatalog.requests.count == 1 && ui.pickers.count == 2, "ASR exact identity cache")
        ui.keyField.text = "second-key"
        ui.credentialEdited()
        check(ui.catalogModels == nil && !ui.catalogLoading && !ui.catalogWantsPicker, "ASR changed draft invalidates")
        ui.credentialEditingEnded()
        check(NagramiXRemoteModelCatalog.requests.count == 2, "ASR new draft reloads")
        ui.keyField.text = "third-key"
        ui.credentialEdited()
        NagramiXRemoteModelCatalog.complete(1, .success(["old-account-model"]))
        check(ui.catalogModels == nil, "ASR old response ignored")
        ui.credentialEditingEnded()
        NagramiXRemoteModelCatalog.complete(2, .success(["new-account-model"]))
        check(ui.catalogModels == ["new-account-model"], "ASR newest response accepted")
        check(NagramiXRemoteModelCatalog.requests[2].key == "third-key", "ASR latest key isolated")
        ui.keyField.text = ""
        ui.credentialEdited()
        ui.credentialEditingEnded()
        check(!ui.catalogLoading && ui.catalogModels == nil && NagramiXRemoteModelCatalog.requests.count == 3, "ASR clear cancels UI without fetching")
    }
}
private func translationCatalogTests() {
    for provider in NagramiXTranslationProvider.allCases.filter({ $0.requiresAPIKey }) {
        NagramiXRemoteModelCatalog.requests = []
        let ui = TranslationCredentialUI()
        ui.page = .credential(provider)
        ui.draftModel = provider.defaultModel
        ui.loadCatalog(provider, openPicker: false)
        check(NagramiXRemoteModelCatalog.requests.isEmpty, "empty translation draft no request")
        ui.loadCatalog(provider, openPicker: true)
        check(ui.alerts == ["missingKey"], "empty translation picker requests key")
        ui.keyField.text = " first-key "
        ui.credentialEdited()
        ui.credentialEditingEnded()
        check(NagramiXRemoteModelCatalog.requests.count == 1, "translation end edit loads catalog")
        check(!NagramiXRemoteModelCatalog.requests[0].speech && NagramiXRemoteModelCatalog.requests[0].provider == provider.rawValue, "translation exact provider")
        check(NagramiXRemoteModelCatalog.requests[0].key == "first-key", "translation exact draft")
        ui.loadCatalog(provider, openPicker: true)
        check(NagramiXRemoteModelCatalog.requests.count == 1 && ui.catalogWantsPicker, "translation pending picker coalesces")
        NagramiXRemoteModelCatalog.complete(0, .success(["available-one", "available-two"]))
        check(!ui.catalogLoading && ui.catalogModels == ["available-one", "available-two"], "translation models arrive")
        check(ui.pickers.count == 1, "translation picker opens")
        ui.pickers[0].completion("available-two")
        check(ui.draftModel == "available-two", "translation current catalog selection")
        ui.keyField.text = "second-key"
        ui.credentialEdited()
        check(ui.catalogModels == nil && !ui.catalogLoading, "translation changed draft invalidates")
        ui.credentialEditingEnded()
        ui.keyField.text = "third-key"
        ui.credentialEdited()
        NagramiXRemoteModelCatalog.complete(1, .success(["old-account-model"]))
        check(ui.catalogModels == nil, "translation old response ignored")
        ui.credentialEditingEnded()
        NagramiXRemoteModelCatalog.complete(2, .success(["new-account-model"]))
        check(ui.catalogModels == ["new-account-model"], "translation new models accepted")
        ui.keyField.text = ""
        ui.credentialEdited()
        ui.credentialEditingEnded()
        check(!ui.catalogLoading && ui.catalogModels == nil && NagramiXRemoteModelCatalog.requests.count == 3, "translation clear no network")
    }
}
@main struct CredentialEntryChecks {
    static func main() {
        credentialTests()
        speechCatalogTests()
        translationCatalogTests()
        print("PASS cloud credential production checks: \(checks)")
    }
}
'''


def ui_boundary(text, speech):
    name = 'SpeechCredentialUI' if speech else 'TranslationCredentialUI'
    picker = 'NagramiXTranscriptionModelPicker' if speech else 'NagramiXTranslationModelPicker'
    field = 'selectedModel' if speech else 'draftModel'
    fields = '''
    let keyField = DraftField()
    let accountField = DraftField()
    let table = DraftTable()
    let presentationData = DraftPresentationData()
    let view = DraftView()
    var isNodeLoaded = true
    var catalogIdentity = ""
    var catalogModels: [String]?
    var catalogLoading = false
    var catalogWantsPicker = false
    var catalogGeneration = UUID()
    var alerts: [String] = []
    var sections: [Int] = []
    func makeSections() -> [Int] { [] }
    func alert(_ value: String) { self.alerts.append(value) }
'''
    page = block(text, '    private enum Page').replace('private ', '')
    methods = '\n'.join(block(text, marker).replace('@objc private ', '').replace('private ', '') for marker in [
        '    @objc private func credentialEdited()',
        '    @objc private func credentialEditingEnded()',
        '    private func loadCatalog(',
        '    private func presentCatalog('])
    return f'class {name} {{\n{page}\n    var page: Page = .settings\n    var {field} = ""\n    var pickers: [{picker}] = []\n    func present(_ picker: {picker}, animated: Bool) {{ self.pickers.append(picker) }}\n{fields}\n{methods}\n}}\n'


def production_harness(source, variant=None):
    speech_ui = (source / (SPEECH + 'Preferences.swift')).read_text()
    translation_ui = (source / (TRANSLATION + 'NagramiXTranslationPreferences.swift')).read_text()
    speech_keys = (source / (SPEECH + 'Credentials.swift')).read_text()
    translation_keys = (source / (TRANSLATION + 'NagramiXTranslationCredentials.swift')).read_text()
    if variant == 'retained_key_read':
        speech_keys = speech_keys.replace('        guard self.enteredByUser(provider) else { return nil }\n', '')
    if variant == 'entry_not_persisted':
        speech_keys = speech_keys.replace('        self.markUserEntry(provider, present: key?.isEmpty == false)\n', '')
    if variant == 'stale_models':
        speech_ui = speech_ui.replace('        self.catalogGeneration = UUID()\n', '')
        # Preserve identity while invalidating key/account so the old callback test
        # specifically proves the generation; original equality also rejects stale keys.
        speech_ui = speech_ui.replace('guard identity == provider.rawValue + "|" + currentAccount + "|" + currentKey else', 'guard true else')
        speech_ui = speech_ui.replace('                let currentKey = (self.keyField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)\n', '')
        speech_ui = speech_ui.replace('                let currentAccount = (self.accountField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)\n', '')
    if variant == 'no_edit_refresh':
        speech_ui = speech_ui.replace('        self.loadCatalog(provider, openPicker: false)\n', '        _ = provider\n')
    settings = [(source / (SPEECH + 'Settings.swift')).read_text(), (source / (TRANSLATION + 'NagramiXTranslationSettings.swift')).read_text()]
    credential = block((source / (TRANSLATION + 'NagramiXTranslationCloud.swift')).read_text(), 'struct NagramiXTranslationCredential')
    error = block((source / (SPEECH + 'NagramiXRemoteModelCatalog.swift')).read_text(), 'enum NagramiXRemoteCatalogError')
    security = (ROOT / 'scripts/tests/NagramiXTranslationKeychainBoundary.swift').read_text()
    files = settings + [speech_keys, translation_keys, credential, security]
    bodies = '\n'.join('\n'.join(l for l in text.splitlines() if not l.startswith('import ')) for text in files)
    bodies = bodies.replace('UserDefaults.standard', 'CredentialTestDefaults.shared')
    return BOUNDARIES.replace('// ERROR_ENUM', error) + bodies + '\n' + ui_boundary(speech_ui, True) + ui_boundary(translation_ui, False) + CREDENTIAL_TESTS + UI_TESTS


def run_swift(source, compiler, temp):
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    reports = []
    negatives = []
    variants = {'retained_key_read': 'fresh retained ASR key ignored',
                'entry_not_persisted': 'ASR exact new key',
                'stale_models': 'ASR old response ignored',
                'no_edit_refresh': 'ASR end edit loads catalog'}
    for optimized in [False, True]:
        mode = 'optimized' if optimized else 'debug'
        for variant in [None, *variants]:
            case = variant or 'production'
            file = temp / (mode + '-' + case + '.swift')
            file.write_text(production_harness(source, variant))
            binary = file.with_suffix('')
            command = [str(compiler), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'module-cache'), str(file), '-o', str(binary)]
            if optimized:
                command.insert(1, '-O')
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            assert result.returncode == 0, result.stdout
            result = subprocess.run([str(binary)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, preexec_fn=no_core)
            if variant:
                assert result.returncode == 91 and ('FAIL ' + variants[variant]) in result.stdout, (case, result.returncode, result.stdout)
                negatives.append({'mode': mode, 'variant': case, 'failure': variants[variant]})
            else:
                assert result.returncode == 0 and 'PASS cloud credential production checks:' in result.stdout, result.stdout
                reports.append({'mode': mode, 'result': result.stdout.strip()})
    parse = temp / 'parse'
    parse.mkdir()
    for i, name in enumerate(PLAN['outputs']):
        file = parse / (str(i) + '.swift')
        file.write_bytes((source / name).read_bytes())
        subprocess.run([str(compiler), '-frontend', '-parse', str(file)], check=True)
    return reports, negatives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    verify(args.source)
    speech = (args.source / (SPEECH + 'Preferences.swift')).read_text()
    translation = (args.source / (TRANSLATION + 'NagramiXTranslationPreferences.swift')).read_text()
    for text in [speech, translation]:
        assert 'self.keyField.textContentType = nil' in text
        assert '#selector(credentialEdited), for: .editingChanged' in text
        assert '#selector(credentialEditingEnded), for: .editingDidEnd' in text
        assert 'importTranslationKey' not in text
    with tempfile.TemporaryDirectory(prefix='cloud-credential-entry-') as folder:
        temp = Path(folder)
        count = guard_checks(args.source, temp)
        runs, negatives = run_swift(args.source, args.swiftc, temp) if args.swiftc else ([], [])
    report = {'outputs': PLAN['outputs'], 'guards': PLAN['guards'], 'fail_closed': count,
              'production_runs': runs, 'semantic_negative_runs': negatives,
              'full_swift_parse_files': 4 if args.swiftc else 0,
              'new_ui_strings': 0,
              'boundaries': 'Real Settings/Credentials and catalog UI handler bodies execute. Defaults, Security.framework, HTTP, UIKit layout/picker/frame presentation are explicit bounded adapters. No real key, network, Apple SDK or physical iPhone used.',
              'apple_sdk': 'pending', 'physical_device': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
