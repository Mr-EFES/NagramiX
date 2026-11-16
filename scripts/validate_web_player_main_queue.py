#!/usr/bin/env python3
"""Проверить исправление трёх одинаковых WebKit crash-стеков0.9.9/build222."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_private_temporary_transcription import execute, save_failed_fixture
from web_player_main_queue_runtime import WEB, fixture, released_fixture, signal_library

STAGE = 'web_player_main_queue'


def apple_check(source, swiftc, folder):
    """Настоящие WKWebView/UIView/Queue API; данные PiP остаются явной границей."""
    folder.mkdir(parents=True, exist_ok=True)
    text = (source / WEB).read_text()
    code = '''import Foundation
import UIKit
@preconcurrency import WebKit
// The unchanged system-PiP data owner is an explicit host; WK APIs below are real.
private final class NagramiXWebSystemPictureInPicture {
 weak var webView:WKWebView?
 var actualMediaChanged:((Bool)->Void)?
 var restore:((@escaping(Bool)->Void)->Void)?
 func stop(){}
}
'''
    code += signal_library(source) + '\n'
    generated = fixture(source)
    code += block(generated, 'private final class NagramiXWebJavaScriptQueue') + '\n'
    code += block(generated, 'private final class NagramiXWebPlayerResources') + '\n'
    code += block(generated, 'private final class Player {') + '\n'
    path = folder / 'WebPlayerMainQueueAPI.swift'
    path.write_text(code)
    parsed = subprocess.run([str(swiftc), '-frontend', '-parse', str(path)], capture_output=True, text=True)
    assert parsed.returncode == 0, parsed.stdout + parsed.stderr
    report = {'swift_parse': 'passed', 'webkit_uikit_typecheck': 'not_run', 'application_sdk': 'pending', 'device': 'pending'}
    if sys.platform == 'darwin':
        sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
        result = subprocess.run([str(swiftc), '-swift-version', '5', '-warnings-as-errors', '-typecheck', '-parse-as-library',
                                 '-sdk', sdk, '-target', 'arm64-apple-ios15.0', '-module-cache-path', str(folder / 'cache'), str(path)],
                                capture_output=True, text=True, timeout=180)
        if result.returncode:
            save_failed_fixture(path, 'web-player-main-queue-api', 'iphoneos', 'typecheck', result)
        assert result.returncode == 0, result.stdout + result.stderr
        report['webkit_uikit_typecheck'] = 'passed'
    return report


def check(source, swiftc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    plan = checked_plan(STAGE)
    text = (source / WEB).read_text()
    previous = (OVERLAY / plan['previous'][WEB]).read_text()
    assert set(plan['inputs']) == {WEB} and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage'] == 'native_pip_refinement'
    assert 'DispatchSemaphore' not in text and 'strongSelf.semaphore.wait()' not in text
    assert 'QueueLocalObject<NagramiXWebPlayerResources>' in text
    # Same player, JS policy/HTML media selection and public PiP API. No format filter.
    for marker in ['private final class NagramiXWebSystemPictureInPicture:',
                   '    func enterNativePictureInPicture()', '    func exitNativePictureInPicture()',
                   '    private func nagramiXPublishPlaybackStatus(']:
        assert block(text, marker) == block(previous, marker), marker
    api = apple_check(source, swiftc, folder / 'apple')
    code = fixture(source)
    runs = execute(swiftc, folder, 'web-player-main-queue', code)
    # The exact released destructor must reproduce the off-main WebKit failure.
    negatives = execute(swiftc, folder, 'released-222-destructor',
                        released_fixture(source, previous), 'WebKit cleanup must run on main')
    variants = [
        ('overlap-evaluations', 'self.running == nil, !self.pending.isEmpty', '!self.pending.isEmpty', 'one WebKit evaluation in flight'),
        ('reorder-commands', 'self.pending.removeFirst()', 'self.pending.removeLast()', 'reentrant enqueue preserves FIFO'),
        ('deliver-stale-result', '!self.invalidated, self.running == command.id', '!self.invalidated', 'duplicate callback cannot advance another command'),
        ('missing-invalidation', 'self.invalidated = true', 'self.invalidated = false', 'close in completion cancels pending and reentrant work'),
        ('retain-pending-owner', 'Queue.mainQueue().async { [weak self] in\n            self?.nagramiXJavaScriptQueue.enqueue(js, completion: completion)', 'Queue.mainQueue().async { [self] in\n            self.nagramiXJavaScriptQueue.enqueue(js, completion: completion)', 'queued enqueue must keep owner weak'),
    ]
    for name, old, new, diagnostic in variants:
        assert old in code, name
        negatives += execute(swiftc, folder, name, code.replace(old, new), diagnostic)
    result = subprocess.run([str(swiftc), '-frontend', '-parse', str(source / WEB)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return {'executions': runs, 'semantic_negatives': negatives, 'apple_api': api,
            'unchanged': 'Gallery button/swipe/native AVKit, web PiP bridge/script, media dimensions, codecs and background/manual-pause policy',
            'boundary': 'Actual queue/enqueue/destructor; real worker Dispatch release/main RunLoop; WebKit/UIKit IO hosts. Real Apple API gate on macOS; live formats/YouTube/iPhone pending.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--swiftc', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='web-player-main-queue-') as d:
        root = Path(d)
        refused = guard_checks(args.source, STAGE, checked_plan(STAGE), root / 'guards')
        result = check(args.source, args.swiftc, root / 'runtime')
    assert manifest(args.source) == before
    result.update(stage=STAGE, loader_refusals=refused, application_sdk='pending', device='pending')
    if args.report: args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
