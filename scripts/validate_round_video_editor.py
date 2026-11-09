#!/usr/bin/env python3
"""Проверить круглое видео, штатный экспорт и совместимость до Apple SDK."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import run, execute
import round_video_editor_runtime as runtime
import round_video_editor_ui_runtime as ui_runtime
import round_video_editor_payload_runtime as payload_runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'round_video_editor'


def contract(source):
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'temporary_playback_identity'
    assert len(plan['inputs']) == 89 and len(plan['guards']) == 75
    assert len(plan['native_inputs']) == 13 and not plan['copies'] and not plan['deletions']
    assert verified_prefix(source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    for name, sha in {**plan['outputs'], **plan['guards']}.items():
        assert digest(source / name) == sha, name
    for name, sha in plan['native_inputs'].items():
        data = (ROOT / 'ios' / plan['previous'][name]).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == sha
    proof = json.loads((ROOT / 'ios/round_video_editor/native-proof.json').read_text())
    assert {item['path']: item['sha'] for item in proof['files']} == plan['native_inputs']
    # The value schema, exporter and native camera are reused, not replaced.
    name = 'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift'
    before = (ROOT / 'ios' / plan['previous'][name]).read_text()
    after = (source / name).read_text()
    assert after == before.replace('withUpdatedVideoTrimRange(_ videoTrimRange: Range<Double>)',
                                   'withUpdatedVideoTrimRange(_ videoTrimRange: Range<Double>?)')
    for suffix in ['ChatMediaEditorCapture.swift', 'ChatMediaEditorScreenCamera.swift',
                   'ChatMediaEditorScreenGallery.swift', 'ChatMediaEditorPager.swift']:
        assert runtime.SCREEN + suffix in plan['guards']
    for name in ['submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorVideoExport.swift',
                 'submodules/TelegramUI/Components/Resources/FetchVideoMediaResource/Sources/FetchVideoMediaResource.swift',
                 'submodules/TelegramUI/Components/VideoMessageCameraScreen/Sources/VideoMessageCameraScreen.swift',
                 'submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift',
                 'submodules/TelegramCore/Sources/Utils/NagramiXOutgoingCopy.swift',
                 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift']:
        assert name in plan['guards'], name
    messages = (source / runtime.MESSAGES).read_text()
    old_messages = (ROOT / 'ios' / plan['previous'][runtime.MESSAGES]).read_text()
    assert block(messages, 'func chatMediaSendMessage(') == block(old_messages, 'func chatMediaSendMessage(')
    assert messages.count('guard let values = nagramiXRoundVideoSendValues(values, duration: duration)') == 2
    video = (source / runtime.VIDEO).read_text()
    assert 'maxDuration: self.nagramiXIsRoundVideo ? min(60.0, mainTrack.duration)' in video
    assert 'minDuration: self.nagramiXIsRoundVideo ? min(chatMediaEditorScrubberMinDuration, mainTrack.duration)' in video
    assert '&& (NagramiXTabSettings.roundVideoEditorEnabled || self.nagramiXIsRoundVideo)' in video
    assert 'cornerCurve = .circular' in video
    controls = (source / (runtime.SCREEN + 'ChatMediaEditorBottomControlsComponent.swift')).read_text()
    assert 'import NagramiXCore' in controls and 'strings.nagramiXRoundVideoTitle' in controls
    build = (source / 'submodules/TelegramUI/Components/ChatMediaEditorScreen/BUILD').read_text()
    assert build.count('"//submodules/NagramiXCore:NagramiXCore"') == 2
    settings = (source / 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift').read_text()
    assert 'case .roundVideo: return 5030' in settings
    assert '.roundVideo(settings.media.roundVideo)' in settings
    assert 'roundVideo: Bool = true' in (source / runtime.SETTINGS).read_text()
    return plan


def changed(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


def negatives(fixtures):
    def mutation(name, suite, old, new, diagnostic):
        return name, changed(fixtures[suite], old, new), diagnostic
    result = [
        mutation('lost-minute-cap', 'range', 'min(duration, start + 60.0, upper)', 'min(duration, start + 90.0, upper)',
                 'whole source selects at most 60 seconds'),
        mutation('lost-selected-start', 'range', 'let start = max(0.0, lower)', 'let start = 0.0',
                 'selected start never resets to zero'),
        mutation('floating-minute-overrun', 'range', 'if end - start > 60.0 { end = end.nextDown }', 'end -= 0.0',
                 'strict cap including floating point starts'),
        mutation('cold-default-off', 'prefs', 'roundVideo: defaults.object(forKey: Key.roundVideo) as? Bool ?? true',
                 'roundVideo: defaults.object(forKey: Key.roundVideo) as? Bool ?? false', 'absent key enables the function'),
        mutation('saved-off-ignored', 'prefs', 'roundVideo: defaults.object(forKey: Key.roundVideo) as? Bool ?? true',
                 'roundVideo: true', 'saved OFF survives reread'),
        mutation('ordinary-file-flag', 'payload', 'flags: isRound ? [.instantRoundVideo] : [.supportsStreaming]',
                 'flags: [.supportsStreaming]', 'real round document attribute'),
        mutation('muted-round-is-gif', 'payload', 'if values.videoIsMuted && values.qualityPreset != .videoMessage {',
                 'if values.videoIsMuted {', 'muted circle never becomes a GIF'),
        mutation('round-album', 'plan', 'item.nagramiXRoundVideo || timers[index]', 'timers[index]',
                 'round messages never enter an album'),
        mutation('restores-current-crop', 'ui', 'rect: before.cropRect, rotation: before.cropRotation',
                 'rect: current.cropRect, rotation: before.cropRotation', 'turning off restores pre-round crop'),
        mutation('stale-gesture-writes-next', 'ui',
                 'guard self.nagramiXRoundGestureItemId == self.pageModel.currentItem.uniqueId else { return }', '',
                 'stale gesture never changes or restores another source'),
        mutation('native-row-overlap', 'toolbar', 'guard hasRoundVideo else', 'guard hasRoundVideo && width < 0 else',
                 'five toolbar targets never overlap back/send'),
    ]
    text = fixtures['payload']
    helper = block(text, 'func nagramiXRoundVideoCaptionMessage(')
    result.append(('lost-caption', text.replace(helper, changed(helper, 'text: caption.text', 'text: ""'), 1),
                   'caption is preserved as ordinary adjacent text'))
    return result


def native_origin_negatives(source, plan, root):
    """Each newly touched native preimage must have its exact official blob SHA."""
    spec = importlib.util.spec_from_file_location(STAGE, ROOT / 'ios' / (STAGE + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tree = root / 'source'
    overlay = root / 'overlay'
    for name in plan['templates']:
        target = overlay / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'ios' / name, target)
    for name in {**plan['inputs'], **plan['guards']}:
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / 'ios' / plan['previous'][name]).read_bytes() if name in plan['previous'] else (source / name).read_bytes())
    before = manifest(tree)
    rejected = []
    for name in plan['native_inputs']:
        corrupt = copy.deepcopy(plan)
        corrupt['native_inputs'][name] = '0' * 40
        (overlay / (STAGE + '_patches.json')).write_text(json.dumps(corrupt))
        try:
            module.apply_round_video_editor(tree, overlay)
        except SystemExit as error:
            assert 'native input origin' in str(error), str(error)
        else:
            raise AssertionError('Invalid native origin accepted: ' + name)
        assert manifest(tree) == before
        rejected.append(name)
    return rejected


def public_api(swiftc, source, root):
    root.mkdir()
    run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', root / 'cache', '-parse-as-library', '-emit-module',
         '-module-name', 'NagramiXMediaSettings', source / runtime.SETTINGS,
         '-emit-module-path', root / 'NagramiXMediaSettings.swiftmodule'])
    caller = root / 'Caller.swift'
    tab = (source / 'submodules/NagramiXCore/Sources/NagramiXTabSettings.swift').read_text()
    caller.write_text('import NagramiXMediaSettings\npublic struct NagramiXTabSettings {\n'
                      + block(tab, '    public static var roundVideoEditorEnabled: Bool {') + '\n}\n'
                      + 'public func checkAPI(_ value: inout NagramiXMediaSettings) { value.roundVideo = false; '
                        '_ = NagramiXTabSettings.roundVideoEditorEnabled }\n')
    run([swiftc, '-swift-version', '5', '-warnings-as-errors', '-module-cache-path', root / 'cache', '-typecheck', '-I', root, caller])
    return {'media_settings_module': 'passed', 'separate_core_caller': 'passed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = contract(args.source)
    before = manifest(args.source)
    fixtures = {name: make(args.source) for name, make in [
        ('range', runtime.range_fixture), ('prefs', runtime.prefs_fixture),
        ('geometry', runtime.geometry_fixture), ('plan', runtime.plan_fixture),
        ('toolbar', runtime.toolbar_fixture), ('ui', ui_runtime.fixture),
        ('payload', payload_runtime.fixture), ('item', payload_runtime.item_fixture)]}
    with tempfile.TemporaryDirectory(prefix='round-video-editor-') as folder:
        root = Path(folder)
        refused = guard_checks(args.source, STAGE, plan, root / 'guards')
        origins = native_origin_negatives(args.source, plan, root / 'native')
        results = []
        for name, fixture in fixtures.items():
            results += execute(args.swiftc, root, name, fixture)
        for name, fixture, diagnostic in negatives(fixtures):
            results += execute(args.swiftc, root, name, fixture, diagnostic)
        api = public_api(args.swiftc, args.source, root / 'api')
        paths = [name for name in plan['outputs'] if name.endswith('.swift')]
        for name in paths:
            run([args.swiftc, '-frontend', '-parse', args.source / name])
    assert before == manifest(args.source)
    run(['python3', args.source / 'build-system/Make/PostboxImportCheck.py', args.source])
    report = {'stage': STAGE, 'outputs': plan['outputs'], 'guards': len(plan['guards']),
              'fail_closed': len(refused), 'native_origin_refusals': len(origins), 'executions': results,
              'swift_parse': len(paths), 'public_api': api, 'source_files': len(before),
              'source_unchanged_by_checks': True, 'native_postbox_imports': 'passed',
              'boundary': 'Production trim/validation, preferences, crop placement/cover-fit, toggle/gesture '
                          'lease, item store, album planner, file attributes, resource JSON and both send '
                          'builders execute in explicit Foundation/UI/AVFoundation/Signal adapters. '
                          'Scalar geometry does not render perspective. Encoders, UIKit, live RPC and '
                          'device frame timing are not emulated or proven.',
              'apple_sdk': 'not_run', 'ipa': 'not_built', 'physical_iphone': 'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('outputs', 'executions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
