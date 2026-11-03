#!/usr/bin/env python3
"""Проверить воспроизведение временных голосовых и штатную анимацию в переписке."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from validate_quick_format import block, manifest

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
PLAN = json.loads((OVERLAY / 'inline_temporary_voice_patches.json').read_text())
A = 'submodules/TelegramCore/Sources/Utils/NagramiXCaptureProtectionPolicy.swift'
O = 'submodules/TelegramUI/Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift'
F = 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift'
W = 'submodules/TelegramUI/Components/AudioWaveformComponent/Sources/AudioWaveformComponent.swift'
R = 'submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_applied(source):
    return all((source / name).is_file() and sha((source / name).read_bytes()) == digest
               for name, digest in PLAN['outputs'].items())


def verify(source):
    assert is_applied(source), 'Inline temporary voice outputs differ'
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
    from validate_expanded_keyboard_handoff import delegate_if_applied as delegate_next
    if delegate_next(args, script):
        return True
    if not is_applied(args.source):
        return False
    verify(args.source)
    with tempfile.TemporaryDirectory(prefix='inline-temporary-voice-prior-') as folder:
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
    spec = importlib.util.spec_from_file_location('inline_temporary_voice', OVERLAY / 'inline_temporary_voice.py')
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
            module.apply_inline_temporary_voice(target, overlay)
        except (SystemExit, OSError):
            pass
        else:
            raise AssertionError('Неверный вход принят: ' + label)
        assert manifest(target) == before, 'Частичная запись: ' + label
        rejected.append(label)
    valid = seed('valid')
    module.apply_inline_temporary_voice(valid, OVERLAY)
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
        (overlay / 'inline_temporary_voice_patches.json').write_text(json.dumps(bad))
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


def stripped(text):
    return 'import Foundation\n' + '\n'.join(line for line in text.splitlines() if not line.startswith('import ')).replace('public ', '')


def runtime_source(source, old_route=False):
    boundary = (ROOT / 'scripts/tests/NagramiXInlineTemporaryVoiceBoundary.swift').read_text()
    opener = (OVERLAY / PLAN['previous'][O]).read_text() if old_route else (source / O).read_text()
    waveform = (source / W).read_text()
    begin = waveform.index('            let timestampAndDuration: (timestamp: Double, duration: Double)?')
    end = waveform.index('\n            let sampleWidth:', begin)
    progress = waveform[begin:end]
    node = (source / F).read_text()
    marker = '        let isViewOnceMessage = isVoice && (message.minAutoremoveOrClearTimeout'
    begin = node.index(marker)
    end = node.index('\n        var state: SemanticStatusNodeState', begin)
    node_mode = node[begin:end]
    begin = node.index('                if isViewOnceMessage && playbackStatus == .playing {', end)
    end = node.index('\n            }\n        }\n        \n        if isViewOnceMessage', begin)
    node_button = node[begin:end]
    return '\n'.join([
        boundary,
        stripped((source / A).read_text()),
        block((source / R).read_text(), 'func nagramiXShouldSuppressViewOnceReceipt('),
        'extension ChatControllerImpl {\n' + block(opener, 'func openViewOnceMediaMessage(') + '\n}',
        '''final class NativeWaveformHarness {
    var playbackStatus: PlaybackStatus?
    var scrubbingTimestampValue: Double?
    private var progress: CGFloat = 0
    func progress(viewOnce: Bool) -> CGFloat {
        let component = WaveformComponent(isViewOnceMessage: viewOnce)
''' + progress + '\n        return self.progress\n    }\n}',
        '''final class NativeVoiceRowHarness {
    private let consumableContentNode = UnreadIndicator()
    var unreadIsHidden: Bool { consumableContentNode.isHidden }
    func isViewOnce(_ message: Message) -> Bool {
        let isVoice = true
''' + node_mode + '''
        return isViewOnceMessage
    }
    func button(_ message: Message, playbackStatus: PlaybackStatus.State, position: Double, duration: Double) -> SemanticStatusNodeState {
        let isVoice = true
''' + node_mode + '''
        let incoming = message.flags.contains(.Incoming)
        let playbackState = (position: position, duration: duration, generationTimestamp: 0.0)
        var state: SemanticStatusNodeState
''' + node_button + '\n        return state\n    }\n}',
        (ROOT / 'scripts/tests/NagramiXInlineTemporaryVoiceTests.swift').read_text(),
    ])


def run_swift(source, swiftc, temp):
    runs = []
    for label, previous in [('current', False), ('old-overlay', True)]:
        suite = temp / (label + '.swift'); suite.write_text(runtime_source(source, previous))
        for optimized in (False, True):
            binary = temp / (label + ('-O' if optimized else '-debug'))
            command = [str(swiftc), '-parse-as-library', '-warnings-as-errors', '-module-cache-path', str(temp / 'cache')]
            if optimized: command += ['-O']
            subprocess.run([*command, str(suite), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60,
                env=dict(__import__('os').environ, XDG_CONFIG_HOME=str(temp / (binary.name + '-prefs'))),
                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if label == 'current':
                assert result.returncode == 0, result.stdout + result.stderr
                runs.append(binary.name + ': ' + result.stdout.strip())
            else:
                assert result.returncode != 0 and 'enabled temporary voice must not open a context overlay' in result.stderr, result.stdout + result.stderr
                runs.append(binary.name + ': прежнее модальное открытие воспроизведено и отвергнуто')
            print(runs[-1], flush=True)
    return runs


def contracts(source):
    capture = (source / A).read_text()
    before_capture = (OVERLAY / PLAN['previous'][A]).read_text()
    for marker in ('public func nagramiXShouldNotifyScreenCapture(', 'var nagramiXAllowsScreenshotBypass:'):
        assert block(capture, marker) == block(before_capture, marker), marker
    route = (source / O).read_text()
    before_route = (OVERLAY / PLAN['previous'][O]).read_text()
    method = block(route, 'func openViewOnceMediaMessage(')
    assert method.index('if self.screenCaptureManager?.isRecordingActive == true') < method.index('if nagramiXCanPlayTemporaryVoiceInline(') < method.index('let configuration = ContextController.Configuration(')
    suffix = method[method.index('        let isIncoming ='):]
    original = block(before_route, 'func openViewOnceMediaMessage(')
    assert suffix == original[original.index('        let isIncoming ='):], 'OFF/native modal branch changed'
    assert 'archived ? .recentActions(message._asMessage()) : .singleMessage(message.id)' in method
    assert 'standalone: archived' in method
    node = (source / F).read_text()
    assert node.count('minAutoremoveOrClearTimeout == viewOnceTimeout || nagramiXCanPlayTemporaryVoiceInline(') == 2
    assert 'isViewOnceMessage: isViewOnceMessage,' in node and 'state = .secretTimeout(position: playbackState.position' in node
    assert 'self.consumableContentNode.isHidden = false' in node
    waveform = (source / W).read_text()
    assert 'sparksView = SparksView()' in waveform and 'playbackProgress = 1.0 - playbackProgress' in waveform
    receipt = (source / R).read_text()
    consume = block(receipt, 'func _internal_markMessageContentAsConsumedInteractively(')
    assert consume.index('if nagramiXShouldSuppressViewOnceReceipt(message) { return }') < consume.index('var updatedAttributes =')
    manager = (source / 'submodules/AccountContext/Sources/MediaManager.swift').read_text()
    assert 'case let .singleMessage(id):\n                return .peer(id.peerId)' in manager
    status = (source / 'submodules/FileMediaResourceStatus/Sources/FileMediaResourceStatus.swift').read_text()
    assert 'return status ?? defaultStatus' in status and 'timestamp: 0.0' in status
    playlist = (source / 'submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist/Sources/PeerMessagesMediaPlaylist.swift').read_text()
    assert 'case .singleMessage = self.messagesLocation' in playlist
    assert 'strongSelf.currentItem = (message, [])' in playlist
    for name in ('submodules/TelegramCore/BUILD', 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/BUILD'):
        build = (source / name).read_text()
        assert 'Sources/**/*.swift' in build, name
    assert '"//submodules/TelegramCore"' in (source / 'submodules/TelegramUI/Components/Chat/ChatMessageInteractiveFileNode/BUILD').read_text()
    assert 'import Foundation\n' in capture
    pipeline = (OVERLAY / 'apply_overlay.py').read_text()
    assert pipeline.index('    apply_recipient_copy_isolation(') < pipeline.index('    apply_inline_temporary_voice(')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    verify(args.source)
    contracts(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-inline-temporary-voice-') as folder:
        temp = Path(folder)
        rejected = guard_checks(args.source, temp)
        runs = run_swift(args.source, args.swiftc, temp) if args.swiftc else []
    if args.swiftc:
        for name in PLAN['outputs']:
            subprocess.run([str(args.swiftc), '-frontend', '-parse', str(args.source / name)], check=True)
    result = {'changed_files': len(PLAN['outputs']), 'guards': len(PLAN['guards']),
              'fail_closed': rejected, 'executions': runs, 'sdk': 'не запускалась',
              'device': 'ожидает проверки на iPhone',
              'runtime': 'actual inline policy, complete openViewOnce method, unchanged receipt policy, native waveform progress and button state; UIKit/player/Postbox DTO boundaries'}
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
