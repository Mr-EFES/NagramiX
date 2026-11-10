#!/usr/bin/env python3
"""Проверить управление одним штатным плеером удалённого кружка до SDK."""
import argparse
import json
from pathlib import Path
import tempfile
import textwrap

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
import archived_round_native_controls_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STAGE='archived_round_native_controls'


def source_contract(source,plan):
    assert plan['required_previous_stage']=='composer_file_attachments'
    assert set(plan['outputs'])=={runtime.ACTION,runtime.ROUND,runtime.SHARED}
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,expected in {**plan['outputs'],**plan['guards']}.items():
        assert digest(source/name)==expected,name
    previous={n:(ROOT/'ios'/plan['previous'][n]).read_text() for n in plan['outputs']}
    current={n:(source/n).read_text() for n in plan['outputs']}
    action=current[runtime.ACTION]
    original=block(previous[runtime.ACTION],'    public func activate(')
    activate=block(action,'    public func activate(')
    old_signature='isCurrent: @escaping () -> Bool, open: @escaping () -> Void)'
    new_signature='isCurrent: @escaping () -> Bool, openAt: ((Double) -> Void)? = nil, open: @escaping () -> Void)'
    branch_start=activate.index('        if message.attributes.contains(where: { $0 is NagramiXArchivedMessageAttribute })')
    branch=activate[branch_start:activate.index('        self.disposable.set((manager.filteredPlaylistState(',branch_start)]
    assert 'first(where: { $0.isInstantVideo })' in branch
    restored_activate=activate.replace(new_signature,old_signature,1).replace(branch,'',1)
    assert restored_activate==original,'Ordinary voice/temporary action changed'
    helper=block(action,'    private func activateArchivedRound(')
    helper_start=action.index('\n    // Loading is not evidence')
    restored=action[:helper_start]+'}\n'
    restored=restored.replace(activate,original,1).replace('import QuartzCore\n','',1)
    assert restored==previous[runtime.ACTION],'Unexpected action changes'
    assert 'manager.globalMediaPlayerState' in helper and 'filteredPlaylistState' not in helper
    assert helper.index('|> timeout(')<helper.index('|> take(1)')<helper.index('|> deliverOnMainQueue')
    for marker in ['account.id == accountId','state.item.id.isEqual(to: itemId)',
                   'reference.media.fileId == file.fileId','reference.media.resource.id == file.resource.id',
                   'manager.playlistControl(.seek(0.0), type: .voice)',
                   'manager.playlistControl(.playback(.play), type: .voice)',
                   'manager.playlistControl(.playback(.togglePlayPause), type: .voice)',
                   'state.status.generationTimestamp','state.status.baseRate','CACurrentMediaTime()']:
        assert marker in helper,marker
    assert 'setPlaylist(' not in helper and 'UniversalVideoNode(' not in helper

    row=current[runtime.ROUND]
    row_activate=block(row,'    private func activateVideoPlayback(')
    old_row_activate=block(previous[runtime.ROUND],'    private func activateVideoPlayback(')
    restored_row=row_activate.replace('            let resourceId = self.media?.resource.id\n','',1)
    restored_row=restored_row.replace(' && self.media?.resource.id == resourceId','',1)
    open_at='''}, openAt: { [weak self] timestamp in
                guard let self, let currentItem = self.item else { return }
                let _ = currentItem.controllerInteraction.openMessage(currentItem.message, OpenMessageParams(mode: .timecode(timestamp)))
            }, open:'''
    assert restored_row.count(open_at)==1
    restored_row=restored_row.replace(open_at,'}, open:',1)
    assert restored_row==old_row_activate
    assert row.replace(row_activate,old_row_activate,1)==previous[runtime.ROUND],'Layout/decoder/ownership changes are outside this fix'

    shared=current[runtime.SHARED]
    old_shared=previous[runtime.SHARED]
    install=block(shared,'    private func nagramiXInstallPlaybackCompletion(')
    scope=block(shared,'    private var nagramiXIsArchivedRoundPlayer:')
    assert 'case .instantVideo?' in scope and 'case let .recentActions(message)' in scope
    assert '$0 is NagramiXArchivedMessageAttribute' in scope
    control=block(shared,'    func control(_ action: SharedMediaPlayerControlAction)')
    original_control=block(old_shared,'    func control(_ action: SharedMediaPlayerControlAction)')
    seek_addition='''                    if self.nagramiXIsArchivedRoundPlayer {
                        // Invalidate a queued completion from the previous run,
                        // then arm the same native player for its new playback cycle.
                        self.nagramiXPlaybackGeneration &+= 1
                        self.currentPlayedToEnd = false
                        self.nagramiXInstallPlaybackCompletion()
                    }
'''
    assert control.replace(seek_addition,'',1)==original_control,'Ordinary native playback controls changed'
    begin=old_shared.index('                        let completedPlaybackGeneration = strongSelf.nagramiXPlaybackGeneration')
    original_completion=old_shared[begin:old_shared.index('                        switch playbackItem {',begin)]
    method_body=install[install.index('        let completedPlaybackGeneration'):install.rindex('\n    }')]
    restored_completion=textwrap.dedent(method_body)+'\n'
    restored_completion=restored_completion.replace('let archivedRound = self.nagramiXIsArchivedRoundPlayer\n','',1)
    restored_completion=restored_completion.replace('let completedPlaybackGeneration = self.nagramiXPlaybackGeneration','let completedPlaybackGeneration = strongSelf.nagramiXPlaybackGeneration',1)
    restored_completion=restored_completion.replace('playbackItem.setActionAtEnd({ [weak self] in','playbackItem.setActionAtEnd({',1).replace('Queue.mainQueue().async { [weak self] in','Queue.mainQueue().async {',1)
    restored_completion=restored_completion.replace('            if archivedRound && strongSelf.nagramiXPlaybackGeneration != completedPlaybackGeneration { return }\n','',1)
    restored_completion=restored_completion.replace('if case .voice = strongSelf.type,','if case .voice = type,',1)
    assert restored_completion==textwrap.dedent(original_completion),'Completion policy changed beyond the archive epoch'
    restored_shared=shared.replace(scope+'\n\n'+install+'\n\n','',1).replace(control,original_control,1)
    restored_shared=restored_shared.replace('                        strongSelf.nagramiXInstallPlaybackCompletion()\n',original_completion,1)
    assert restored_shared==old_shared,'Unexpected native player change'

    # Real declarations compile in the fixture. Verify the platform-only fields against their source.
    status=(source/'submodules/MediaPlayer/Sources/MediaPlayer.swift').read_text()
    for name in ['generationTimestamp','duration','timestamp','baseRate']:
        assert 'public let '+name+': Double' in block(status,'public struct MediaPlayerStatus:')
    assert 'import QuartzCore\n' in action
    bubble=(source/'submodules/TelegramUI/Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift').read_text()
    assert 'let nagramiXContentAlpha: CGFloat = nagramiXIsArchived ? 0.5 : 1.0' in bubble
    assert 'strongSelf.clippingNode.alpha = nagramiXContentAlpha' in bubble
    native=(source/'submodules/TelegramUniversalVideoContent/Sources/NativeVideoContent.swift').read_text()
    assert 'NagramiXArchivedInstantVideoId(messageId: messageId, fileId: fileReference.media.fileId, resourceId: fileReference.media.resource.id)' in native


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    plan=checked_plan(STAGE)
    source_contract(args.source,plan)
    initial=manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='archived-round-controls-') as temporary:
        folder=Path(temporary)
        refusals=guard_checks(args.source,STAGE,plan,folder/'guards')
        code=runtime.fixture(args.source)
        runs=execute(args.swiftc,folder,'archive-native-controls',code)
        for name,mutated,diagnostic in runtime.negatives(code):
            runs+=execute(args.swiftc,folder,name,mutated,diagnostic)
        for name in plan['outputs']:
            run([args.swiftc,'-frontend','-parse',args.source/name])
    assert manifest(args.source)==initial
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),
            'loader_refusals':len(refusals),'executions':runs,'swift_parse':len(plan['outputs']),
            'source_files':len(initial),'source_unchanged_by_checks':True,
            'boundary':'Complete production action and actual round-row caller execute with native playlist/item identity, playback state models and SignalKit filter/timeout/take/delivery/disposal. Queue/Timer/monotonic time and Telegram IO are explicit adapters. All geometry, 50% presentation, manager, content IDs, decoder, archive, temporary receipts and ASR remain exact guards; physical frames, UIKit, AVFoundation and server require Apple SDK/iPhone.',
            'apple_sdk':'not_run','device':'pending'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('outputs','executions')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
