#!/usr/bin/env python3
"""Проверить единый штатный плеер кружков без сборки приложения или IPA."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import execute, run
from validate_round_video_replay_stability import playback_module_tests
import round_native_playback_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STAGE='round_native_playback'


def contract(source):
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='release_092_settings_compile'
    assert len(plan['inputs'])==7 and len(plan['guards'])==26
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():
        assert digest(source/name)==sha,name
    native=(source/runtime.NATIVE).read_text()
    stock=(ROOT/'ios'/STAGE/'NativeRoundLayout.inc').read_text()
    assert block(native,'    func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition)')==stock.rstrip('\n')
    assert hashlib.sha256((stock).encode()).hexdigest()==plan['templates'][STAGE+'/NativeRoundLayout.inc']
    shared=(source/runtime.SHARED).read_text()
    assert '|| nagramiXCanUseTemporaryMediaActions(item.message)) ? item.message.id : nil' not in shared
    row=(source/runtime.ROUND).read_text()
    assert row.count('nagramiXArchivedMessageId: nagramiXArchivedInstantVideo ? item.message.id : nil')==1
    controller=(source/runtime.CONTROLLER).read_text()
    assert 'import PeerMessagesMediaPlaylist\n' in controller
    assert '"//submodules/TelegramUI/Components/MediaManager/PeerMessagesMediaPlaylist"' in (source/'submodules/TelegramUI/BUILD').read_text()
    # Retention, copy, reply, receipts and native content ownership/decoration
    # remain exact source guards. The change creates no new playback engine.
    assert runtime.MANAGER in plan['guards']
    assert 'submodules/TelegramCore/Sources/Utils/NagramiXMessageArchive.swift' in plan['guards']
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();plan=contract(args.source);before=manifest(args.source)
    fixtures={key:getattr(runtime,key)(args.source) for key in ['ownership','recording','presentation','activation']}
    with tempfile.TemporaryDirectory(prefix='nagramix-round-native-') as temporary:
        root=Path(temporary);refused=guard_checks(args.source,STAGE,plan,root/'guards')
        results=[]
        for name,text in fixtures.items():results+=execute(args.swiftc,root,name,text)
        for name,text,reason in runtime.negatives(fixtures):results+=execute(args.swiftc,root,name,text,reason)
        results+=playback_module_tests(args.source,args.swiftc,root/'selected-player-modules')
        for name in plan['outputs']:run([args.swiftc,'-frontend','-parse',args.source/name])
    assert before==manifest(args.source)
    run(['python3',args.source/'build-system/Make/PostboxImportCheck.py',args.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'loader_refusals':len(refused),'executions':results,'swift_parse':len(plan['outputs']),'source_files':len(before),'source_unchanged_by_checks':True,'native_round_inner_geometry':'exact Telegram13.2 function','native_postbox_imports':'passed','boundary':'Production content identity, native manager attachment/subscriber handoff, capture gates, idle cover, footer frame code and activation execute in explicit media/UI/network adapters. The actual unchanged playlist action also compiles against separate Core/Signal modules. UIKit, decoder pixels, real time animation and live network/device behavior are not tested.','apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['outputs','executions']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
