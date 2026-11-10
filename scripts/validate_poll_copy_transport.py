#!/usr/bin/env python3
"""Проверить полный payload самостоятельного видеоопроса и резервные пути медиа."""
import argparse
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
import poll_copy_transport_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STAGE='poll_copy_transport'


def contract(source):
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='round_native_playback'
    assert set(plan['inputs'])=={runtime.COPY,runtime.UPLOAD}
    assert len(plan['guards'])==27 and not plan['copies'] and not plan['deletions']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():assert digest(source/name)==sha,name
    old=(ROOT/'ios'/plan['previous'][runtime.COPY]).read_text();new=(source/runtime.COPY).read_text()
    marker='private func nagramiXCopyPollAsNew('
    assert old.replace(block(old,marker),block(new,marker))==new
    # Sending/retry/ownership outside the poll path remains native and checked.
    previous=(ROOT/'ios'/plan['previous'][runtime.UPLOAD]).read_text();upload=(source/runtime.UPLOAD).read_text()
    for marker in ['func nagramiXCopyDeliverySignal<Value, Failure>(', 'func nagramiXCopyRefreshSignal<Value>(', 'func nagramiXCopyRefreshedMedia(', 'private func uploadedMediaImageContent(', 'private func uploadedMediaFileContent(']:
        assert block(previous,marker)==block(upload,marker),marker
    assert 'import MtProtoKit\n' in upload
    assert '"//submodules/MtProtoKit:MtProtoKit"' in (source/'submodules/TelegramCore/BUILD').read_text()
    schema=(source/'submodules/TelegramApi/swift_scheme.tl').read_text()
    assert 'inputPollAnswer#199fed96 flags:# text:TextWithEntities media:flags.0?InputMedia = PollAnswer;' in schema
    assert 'inputMediaPoll#883a4108 flags:# poll:Poll correct_answers:flags.0?Vector<int> attached_media:flags.3?InputMedia solution:flags.1?string solution_entities:flags.1?Vector<MessageEntity> solution_media:flags.2?InputMedia = InputMedia;' in schema
    # These exact guards include native repost, single/broadcast recipient batch,
    # delayed/silent sends, outbox ACK/IDs and all previous round-player fixes.
    for name in ['submodules/TelegramCore/Sources/State/PendingMessageManager.swift','submodules/TelegramUI/Sources/ChatControllerForwardMessages.swift','submodules/TelegramUI/Sources/SharedMediaPlayer.swift']:
        assert name in plan['guards'],name
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();plan=contract(args.source);before=manifest(args.source)
    fixture=runtime.fixture(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-poll-copy-') as temporary:
        root=Path(temporary);refused=guard_checks(args.source,STAGE,plan,root/'guards')
        results=execute(args.swiftc,root,'poll-copy-transport',fixture)
        for name,text,reason in runtime.negatives(fixture):results+=execute(args.swiftc,root,name,text,reason)
        for name in plan['outputs']:run([args.swiftc,'-frontend','-parse',args.source/name])
    assert before==manifest(args.source)
    run(['python3',args.source/'build-system/Make/PostboxImportCheck.py',args.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'loader_refusals':len(refused),'executions':results,'swift_parse':len(plan['outputs']),'source_files':len(before),'source_unchanged_by_checks':True,'native_postbox_imports':'passed','boundary':'Actual poll model fields, copier, complete poll sender branch, reference resolver, refresher and native SignalKit execute. Typed API/Postbox/network/byte I/O are explicit adapters. This verifies final payload and bounded fallback for the reported nine-option video poll, not live Telegram acceptance or device delivery.','apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending','exact_rpc_error_from_user_device':'not_available'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['outputs','executions']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
