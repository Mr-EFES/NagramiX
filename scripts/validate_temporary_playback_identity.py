#!/usr/bin/env python3
"""Проверить разделение одноразового оригинала, штатного плеера и удаления."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import run, execute
import temporary_playback_identity_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]
STAGE = 'temporary_playback_identity'


def contract(source):
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='local_copy_delivery'
    assert len(plan['inputs'])==9 and not plan['copies'] and not plan['deletions']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():
        assert digest(source/name)==sha,name
    texts={name:(source/name).read_text() for name in plan['outputs']}
    archive=texts[runtime.ARCHIVE]
    readonly=block(archive,'    public func temporaryInteractionMessage(')
    for bad in ['self.persist(', 'markTemporaryExpired(', 'snapshotForExpiredMessage(', '.queue.', '.network.', 'captureTemporaryBeforeViewing(']:
        assert bad not in readonly,bad
    assert 'var originalViewOnce: Bool? = nil' in archive
    assert 'isViewOnce: record.originalViewOnce == true' in archive
    render=block(archive,'    private func renderDeletedRecord(')
    assert 'AutoremoveTimeoutMessageAttribute(' not in render and 'AutoclearTimeoutMessageAttribute(' not in render
    circle=texts[runtime.ROUND]
    assert 'hasSeek: !requiresDisposableViewOnce, sparks: isViewOnceMessage' in circle
    assert 'self.videoNode?.isHidden = isSecretMedia || requiresDisposableViewOnce' in circle
    assert 'nagramiXArchivedMessageId: nagramiXArchivedInstantVideo ? item.message.id : nil' in circle
    assert 'autoplayVideo && !requiresDisposableViewOnce' in circle
    voice=texts[runtime.UI+'Components/Chat/ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift']
    assert voice.count('isVoice && nagramiXIsViewOnceMessage(')==2
    assert 'if !isSecretMedia && nagramiXIsViewOnceMessage(message)' in texts[runtime.UI+'Components/Chat/ChatMessageInteractiveMediaNode/Sources/ChatMessageInteractiveMediaNode.swift']
    opening=texts[runtime.UI+'Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift']
    before=(ROOT/'ios'/plan['previous'][runtime.UI+'Sources/Chat/ChatControllerOpenViewOnceMediaMessage.swift']).read_text()
    # Entire stock disposable route and capture alert are unchanged. Only the
    # retention shortcut switches to normal, complete controller callbacks.
    marker='        let isIncoming = message.effectivelyIncoming(self.context.account.peerId)'
    assert opening[opening.index(marker):]==before[before.index(marker):]
    assert opening[:opening.index('        if nagramiXCanUseTemporaryMediaActions(')]==before[:before.index('        if nagramiXCanUseTemporaryMediaActions(')]
    assert 'navigationController: nil' not in opening[:opening.index(marker)]
    bubble=(source/(runtime.UI+'Components/Chat/ChatMessageBubbleItemNode/Sources/ChatMessageBubbleItemNode.swift')).read_text()
    assert 'let nagramiXContentAlpha: CGFloat = nagramiXIsArchived ? 0.5 : 1.0' in bubble
    assert 'nagramiXViewOnceReplayLabel' not in bubble
    # Native send/consume/read paths, storage and previous copy/PiP fixes must
    # stay exact guards. No outgoing TTL conversion or extra receipt is added.
    for name in ['submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift',
                 'submodules/TelegramCore/Sources/TelegramEngine/Messages/MarkMessageContentAsConsumedInteractively.swift',
                 'submodules/TelegramCore/Sources/State/ManagedSecretChatOutgoingOperations.swift',
                 'submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift',
                 'submodules/NagramiXTranscription/Sources/Runtime.swift']:
        assert name in plan['guards'],name
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    plan=contract(args.source)
    before=manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='temporary-playback-identity-') as folder:
        root=Path(folder)
        rejected=guard_checks(args.source,STAGE,plan,root/'guards')
        archive=runtime.archive(args.source);ui=runtime.ui(args.source)
        results=execute(args.swiftc,root,'archive',archive)+execute(args.swiftc,root,'native-routing',ui)
        results+=execute(args.swiftc,root,'consumption',runtime.consumption(args.source))
        for name,fixture,diagnostic in runtime.negatives(archive,ui):
            results+=execute(args.swiftc,root,name,fixture,diagnostic)
        for name in plan['outputs']:
            run([args.swiftc,'-frontend','-parse',args.source/name])
    assert before==manifest(args.source)
    run(['python3',args.source/'build-system/Make/PostboxImportCheck.py',args.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),
            'fail_closed':len(rejected),'executions':results,'swift_parse':len(plan['outputs']),
            'source_files':len(before),'source_unchanged_by_checks':True,'native_postbox_imports':'passed',
            'boundary':'Production archive persistence, source provenance, attribute codec, eligibility, '
                       'route/activation and playlist filter snippets execute in explicit storage/UI/network '
                       'adapters. Original sending and receipt/secret-history producers remain pinned. '
                       'No Apple SDK, UIKit rendering, live Telegram RPC or physical device is proven.',
            'apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('outputs','executions')},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
