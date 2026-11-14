#!/usr/bin/env python3
"""Verify deferred story-source hiding, cancellation and restoration."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, guard_checks, OVERLAY
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import story_avatar_visibility_runtime as runtime

STAGE = 'story_avatar_visibility'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--swiftc', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    plan = checked_plan(STAGE)
    assert plan['required_previous_stage'] == 'archived_playlist_lifetime'
    assert set(plan['inputs']) == {runtime.SCREEN, runtime.OPEN, runtime.PROFILE}
    assert len(plan['guards']) == 17 and not plan['copies'] and not plan['deletions']
    assert verified_prefix(args.source) == LATE_SOURCE_STAGES.index(STAGE) + 1
    before = (OVERLAY / plan['previous'][runtime.SCREEN]).read_text()
    after = (args.source / runtime.SCREEN).read_text()
    for marker in [
        '    private func nagramiXUsesAnonymousViewing(',
        '    fileprivate func nagramiXConfirmNavigation(',
        '    fileprivate func nagramiXCanMarkStoryAsSeen(',
        '    public func nagramiXPresent(',
        '    public func nagramiXPush(from parentController: ViewController, completion: @escaping () -> Void = {}) {',
        '    public func nagramiXPush(from navigationController: NavigationController, completion: @escaping () -> Void = {}) {',
        'private final class NagramiXStoryConfirmationController:',
    ]:
        assert runtime.declaration(before, marker) == runtime.declaration(after, marker), 'Approval/read/navigation logic changed: ' + marker
    hide = '            self.nagramiXSourceTransition?.setSourceHidden(true)\n'
    restore = '        self.nagramiXSourceTransition?.setSourceHidden(false)\n'
    comment = '            // Keep the source visible while confirmation is pending or cancelled.\n'
    assert after.count(hide) == after.count(restore) == 1
    marker = '    override public func viewDidAppear('
    assert block(after, marker).replace(comment + hide, '', 1) == block(before, marker), 'Native animation/lifecycle changed'
    # Existing transition-out bodies retain their original animation/snapshot
    # and completion callbacks. Only preparing a source becomes side-effect free.
    old_open = (OVERLAY / plan['previous'][runtime.OPEN]).read_text()
    new_open = (args.source / runtime.OPEN).read_text()
    for text, count in [(new_open, 2), ((args.source / runtime.PROFILE).read_text(), 2)]:
        assert text.count('sourceHiddenUpdated:') == count
    assert new_open.count('avatarNode.isHidden = true') == 0
    for marker in ['            transitionOut: { [weak avatarNode]', '        setProgress(signal)']:
        if marker.startswith('            transitionOut:'):
            assert block(old_open, marker) == block(new_open, marker)
        else:
            assert old_open[old_open.index(marker):] == new_open[new_open.index(marker):]
    state = manifest(args.source)
    code = runtime.fixture(args.source)
    assert code.count(hide) == code.count(restore) == 1
    with tempfile.TemporaryDirectory(prefix='story-avatar-visibility-') as folder:
        temporary = Path(folder)
        refused = guard_checks(args.source, STAGE, plan, temporary / 'guards')
        runs = execute(args.swiftc, temporary, STAGE, code)
        old_source = temporary / 'original76'
        for name in {**plan['inputs'], **plan['guards']}:
            path = old_source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = (OVERLAY / plan['previous'][name]).read_bytes() if name in plan['previous'] else (args.source / name).read_bytes()
            path.write_bytes(data)
        runs += execute(args.swiftc, temporary, 'original76-hides-before-confirmation', runtime.fixture(old_source), 'source remains visible before confirmation')
        runs += execute(args.swiftc, temporary, 'missing-appearance-hide', code.replace(hide, '', 1), 'real viewer appearance hides transition source')
        runs += execute(args.swiftc, temporary, 'missing-disposal-restore', code.replace(restore, '', 1), 'viewer disposal restores original avatar')
        weak = 'sourceHiddenUpdated: { [weak avatarNode] hidden in'
        assert code.count(weak) == 2
        runs += execute(args.swiftc, temporary, 'retaining-original-avatar', code.replace(weak, 'sourceHiddenUpdated: { [avatarNode = Optional(avatarNode)] hidden in'), 'transition callback weakly captures original avatar')
        run([args.swiftc, '-frontend', '-parse', *[args.source / name for name in plan['inputs']]])
    assert state == manifest(args.source), 'Checks mutated final application source'
    report = {
        'stage': STAGE, 'runtime_paths': list(plan['inputs']), 'guards': len(plan['guards']),
        'loader_refusals': len(refused), 'executions': runs,
        'root_cause': 'OpenStories hides the avatar while building TransitionIn, before the confirmation gate. Cancelled/unpresented viewers never invoke native transitionOut.completed, leaving the list/profile source hidden.',
        'scope': 'Four source callbacks (peer/avatar, archive, profile avatar and expanded indicator) defer hiding until the real viewer first appears. Viewer disposal restores its original weakly captured source even if no destination transition is available. Existing approval, incognito, read receipts, media, animation and transitionOut bodies are unchanged.',
        'boundary': 'Actual confirmation/push/seen methods, TransitionIn, avatar preparation callbacks, viewer viewDidAppear/deinit and real SwiftSignalKit execute. UIKit geometry/drawing/navigation, account/story state and OS timers are explicit adapters; no Apple SDK compilation or physical iPhone rendering.',
        'source_unchanged_by_checks': True, 'full_application_sdk': 'pending', 'physical_iphone': 'pending',
        'new_sdk_actions_ipa_started': False,
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
