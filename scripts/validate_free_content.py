#!/usr/bin/env python3
"""Проверить единый переключатель «Свободный контент», миграцию и восстановление ограничений."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'free_content_patches.json').read_text())
A = 'submodules/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift'
C = 'submodules/TelegramCore/Sources/Settings/ContentSettings.swift'
P = 'submodules/TelegramCore/Sources/Utils/PeerUtils.swift'
U = 'submodules/TelegramUI/Sources/ChatController.swift'
MATCHING = 'submodules/PlatformRestrictionMatching/Sources/PlatformRestrictionMatching.swift'
CAPTURE = 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift'
READ_MODE = 'submodules/NagramiXMediaSettings/Sources/NagramiXReadModeSettings.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_applied(source):
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest
               for name, digest in PLAN['outputs'].items())


def verify(source):
    assert is_applied(source), 'Free content outputs differ'
    for name, digest in PLAN['guards'].items():
        assert sha((source / name).read_bytes()) == digest, name
    for name, digest in PLAN['templates'].items():
        assert sha((OVERLAY / name).read_bytes()) == digest, name


def reverse(source, prior):
    names = set(PLAN['inputs'])
    for path in OVERLAY.glob('*_patches.json'):
        item = json.loads(path.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(item.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update(['Telegram/Telegram-iOS/en.lproj/Localizable.strings',
                  'submodules/TelegramPresentationData/Sources/PresentationData.swift',
                  'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift'])
    for name in names:
        path = OVERLAY / PLAN['previous'][name] if name in PLAN['previous'] else source / name
        if path.is_file():
            target = prior / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


def delegate_if_applied(args, script):
    from validate_recipient_copy_isolation import delegate_if_applied as delegate_next
    if delegate_next(args, script):
        return True
    if not is_applied(args.source):
        return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='free-content-prior-') as folder:
        prior = Path(folder)
        reverse(args.source, prior)
        arguments = []
        for key, value in vars(args).items():
            if key == 'source': arguments += ['--source', str(prior)]
            elif value is True: arguments.append('--' + key.replace('_', '-'))
            elif value is not None and value is not False: arguments += ['--' + key.replace('_', '-'), str(value)]
        if getattr(args, 'swiftc', None) and hasattr(args, 'upstream') and args.upstream is None:
            arguments += ['--upstream', str(args.source)]
        subprocess.run([sys.executable, str(script), *arguments], check=True)
    return True


def guard_checks(source, temp):
    spec = importlib.util.spec_from_file_location('free_content', OVERLAY / 'free_content.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def seed(label):
        target = temp / label
        for name in {**PLAN['inputs'], **PLAN['guards']}:
            data = (OVERLAY / PLAN['previous'][name]).read_bytes() if name in PLAN['previous'] else (source / name).read_bytes()
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return target
    rejected = []
    def reject(target, label, overlay=OVERLAY):
        before = manifest(target)
        try:
            module.apply_free_content(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_free_content(valid, OVERLAY)
    assert all((valid / name).read_bytes() == (source / name).read_bytes() for name in PLAN['outputs'])
    reject(valid, 'повторное применение')
    for name in {**PLAN['inputs'], **PLAN['guards']}:
        for kind in ('missing', 'drift'):
            target = seed(str(len(rejected)))
            path = target / name
            if kind == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes() + b'\n// drift\n')
            reject(target, kind + ' ' + name)
    mutations = []
    for field in ('inputs', 'outputs', 'guards', 'templates'):
        bad = copy.deepcopy(PLAN)
        bad[field][next(iter(bad[field]))] = '0' * 64
        mutations.append((field + '-SHA', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations'][A][0][0] += ' broken'
    mutations.append(('anchor', bad))
    bad = copy.deepcopy(PLAN)
    bad['previous'][A] = '../outside.swift'
    mutations.append(('template-traversal', bad))
    bad = copy.deepcopy(PLAN)
    for field in ('inputs', 'outputs', 'previous', 'operations'):
        bad[field]['../outside.swift'] = bad[field].pop(A)
    mutations.append(('source-traversal', bad))
    bad = copy.deepcopy(PLAN)
    bad['operations']['/outside.swift'] = bad['operations'].pop(A)
    mutations.append(('operation-path', bad))
    for label, bad in mutations:
        overlay = temp / ('bad-' + label)
        overlay.mkdir()
        for path in PLAN['templates']:
            destination = overlay / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((OVERLAY / path).read_bytes())
        (overlay / 'free_content_patches.json').write_text(json.dumps(bad))
        reject(seed('root-' + label), label, overlay)
    for label, name in [('input-symlink', A), ('guard-symlink', next(iter(PLAN['guards'])))]:
        target = seed(label)
        path = target / name
        external = temp / (label + '.swift')
        external.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external)
        reject(target, label)
    return rejected


def without_imports(text):
    return '\n'.join(line for line in text.splitlines() if not line.startswith('import '))


def runtime_source(source, old_peer=False, old_message=False):
    peer_source = (OVERLAY / PLAN['previous'][P]).read_text() if old_peer else (source / P).read_text()
    matching = (OVERLAY / PLAN['previous'][MATCHING]).read_text() if old_message else (source / MATCHING).read_text()
    controller = (source / U).read_text()
    observer_start = controller.index('        self.nagramiXFreeContentObserver = NotificationCenter.default.addObserver(')
    observer_end = controller.index('        self.nagramiXRefreshFreeContent()\n', observer_start) + len('        self.nagramiXRefreshFreeContent()\n')
    observer = controller[observer_start:observer_end]
    cleanup = next(line for line in controller.splitlines() if 'if let observer = self.nagramiXFreeContentObserver {' in line)
    return '\n'.join([
        (ROOT / 'scripts/tests/NagramiXFreeContentBoundary.swift').read_text(),
        block((source / C).read_text(), 'public struct ContentSettings:'),
        'public extension Peer {\n' + block(peer_source, 'func restrictionText(') + '\n}',
        without_imports(matching),
        without_imports((source / CAPTURE).read_text()),
        '''private final class ControllerHarness {
    var isNodeLoaded = true
    let chatDisplayNode = DisplayNode()
    var forcedUpdates = 0
    private var nagramiXFreeContentObserver: NSObjectProtocol?
    private var nagramiXFreeContentEnabled = NagramiXPrivacySettings.current.allowsFreeContent
    init() {
''' + observer + '''
    }
    deinit {
''' + cleanup + '''
    }
    private func updateChatPresentationInterfaceState(transition: ContainedViewLayoutTransition, interactive: Bool, force: Bool, _ body: (Int) -> Int) {
        precondition(force && !interactive && body(5) == 5)
        forcedUpdates += 1
    }
''' + block(controller, 'private func nagramiXRefreshFreeContent()') + '\n}',
        (ROOT / 'scripts/tests/NagramiXFreeContentTests.swift').read_text(),
    ])


def run_swift(source, swiftc, temp):
    runs = []
    modules = temp / 'modules'
    modules.mkdir()
    subprocess.run([str(swiftc), '-emit-module', '-parse-as-library', '-warnings-as-errors',
                    '-module-cache-path', str(temp / 'cache'),
                    '-module-name', 'NagramiXMediaSettings', str(source / A), str(source / READ_MODE),
                    '-emit-module-path', str(modules / 'NagramiXMediaSettings.swiftmodule')], check=True)
    core = temp / 'CorePolicy.swift'
    core.write_text('import Foundation\nimport NagramiXMediaSettings\n' + block((source / C).read_text(), 'public struct ContentSettings:') + '\n')
    subprocess.run([str(swiftc), '-emit-module', '-parse-as-library', '-warnings-as-errors',
                    '-module-cache-path', str(temp / 'cache'),
                    '-module-name', 'TelegramCore', '-I', str(modules), str(core),
                    '-emit-module-path', str(modules / 'TelegramCore.swiftmodule')], check=True)
    client = temp / 'ModuleClient.swift'
    client.write_text('import TelegramCore\nimport NagramiXMediaSettings\nfunc checkSettingsImports() -> Bool { ContentSettings.default.nagramiXAllowsFreeContent == NagramiXPrivacySettings.current.allowsFreeContent }\n')
    subprocess.run([str(swiftc), '-typecheck', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache'), '-I', str(modules), str(client)], check=True)
    runs.append('module-interface: actual privacy module and Core accessor compile with explicit imports')
    for label, old_peer, old_message in [('current', False, False), ('old-peer', True, False), ('old-message', False, True)]:
        source_path = temp / (label + '.swift')
        source_path.write_text(runtime_source(source, old_peer, old_message))
        for optimized in (False, True):
            binary = temp / (label + ('-O' if optimized else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized: command += ['-O']
            subprocess.run([*command, str(source / A), str(source / READ_MODE), str(source_path), '-o', str(binary)], check=True)
            env = dict(os.environ, XDG_CONFIG_HOME=str(temp / (binary.name + '-prefs')))
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60, env=env,
                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                runs.append(binary.name + ': ' + result.stdout.strip())
                for expected in ('true', 'false'):
                    subprocess.run([str(binary), '--write', expected], env=env, check=True, timeout=30)
                    subprocess.run([str(binary), '--read', expected], env=env, check=True, timeout=30)
                runs.append(binary.name + ': ON/OFF сохраняются в отдельных холодных процессах')
            else:
                expected = 'enabled content must remove platform notice from peer' if old_peer else 'enabled content must remove platform notice from message'
                assert result.returncode != 0 and expected in result.stderr, result.stdout + result.stderr
                runs.append(binary.name + ': прежнее ограничение воспроизведено и отвергнуто')
            print(runs[-1], flush=True)
    return runs


def contracts(source):
    before = (OVERLAY / PLAN['previous'][A]).read_text()
    current = (source / A).read_text()
    for name in ('public static func read(', 'public static func update(', 'public func requiresScreenshotProtection('):
        assert block(before, name) == block(current, name), name
    assert 'case storyReads, online, typing, readOnAction, screenshotBypass' in current
    assert 'private static let key = "nagramix.privacy.individual.v2"' in current
    controller = (source / 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
    assert controller.count('.privacyToggle(.screenshotBypass, privacy[.screenshotBypass])') == 1
    assert 'case .screenshotBypass: return 154' in controller and 'case .screenshotBypass: return 498' in controller
    for language, title in [('ru', 'Свободный контент'), ('en', 'Free Content')]:
        resources = (source / f'submodules/NagramiXCore/Resources/{language}.lproj/Localizable.strings').read_text()
        line = f'"NagramiX.Privacy.screenshotBypass" = "{title}";'
        assert resources.count(line) == 1, language
    native_controller = (source / U).read_text()
    assert 'import NagramiXMediaSettings\n' in native_controller, 'Missing direct settings module import'
    assert 'import NagramiXMediaSettings\n' in (source / C).read_text(), 'Missing Core settings module import'
    assert '//submodules/NagramiXMediaSettings:NagramiXMediaSettings' in (source / 'submodules/TelegramUI/BUILD').read_text()
    assert block(native_controller, 'override public func viewWillAppear(').count('self.nagramiXRefreshFreeContent()') == 1
    assert native_controller.count('NotificationCenter.default.removeObserver(observer) }\n        let _ = ChatControllerCount.modify') == 1
    assert '//submodules/NagramiXMediaSettings:NagramiXMediaSettings' in (source / 'submodules/TelegramCore/BUILD').read_text()
    assert '//submodules/TelegramCore:TelegramCore' in (source / 'submodules/PlatformRestrictionMatching/BUILD').read_text()
    calls = (OVERLAY / 'apply_overlay.py').read_text()
    assert calls.index('    apply_archive_chat_scope(') < calls.index('    apply_free_content(')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    from validate_inline_temporary_voice import delegate_if_applied as delegate_latest
    if delegate_latest(args, Path(__file__)):
        return
    verify(args.source)
    contracts(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-free-content-check-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp)
        runs = run_swift(args.source, args.swiftc, temp) if args.swiftc else []
    if args.swiftc:
        for name in PLAN['outputs']:
            if name.endswith('.swift'):
                subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'changed_files': len(PLAN['outputs']), 'guards': len(PLAN['guards']),
              'fail_closed': rejected, 'executions': runs, 'sdk': 'не запускалась',
              'device': 'ожидает проверки на iPhone',
              'runtime': 'production privacy model, content settings and peer/message restrictions, capture policy and chat refresh; UI/Postbox DTO boundaries; Foundation preferences and notifications real'}
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
