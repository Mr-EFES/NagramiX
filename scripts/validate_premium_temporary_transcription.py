#!/usr/bin/env python3
"""Проверить Premium ASR по отдельному файлу без original-ID RPC и скрытого Apple."""
import argparse,json,re,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_local_copy_delivery import execute,run
from validate_premium_temporary_transcription_native_api import check as native_check
import premium_temporary_transcription_runtime as runtime

ROOT=Path(__file__).resolve().parents[1];STAGE='premium_temporary_transcription';ASR='submodules/NagramiXTranscription/Sources/';CORE='submodules/TelegramCore/Sources/TelegramEngine/Messages/';MENU='submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift'

def source_contract(source,plan):
    assert len(plan['inputs'])==4 and len(plan['guards'])==18
    before={n:(ROOT/'ios'/p).read_text() for n,p in plan['previous'].items()};current={n:(source/n).read_text() for n in plan['inputs']}
    native=CORE+'Transcription.swift';assert current[native].startswith(before[native]),'Original-ID transcription/rating changed'
    file_api=block(current[native],'    func nagramiXTranscribeAudioFile(')
    assert all(s not in file_api for s in ['messageId','msgId','inputPeer','transcribeAudio(peer:','readMessage','enqueueMessage','retainTelegramTranscription'])
    assert 'transcribeAudioFile(file: namedFile), automaticFloodWait: false' in file_api
    settings=ASR+'Settings.swift';s=current[settings].replace(', insufficientMemory, premiumRequired',', insufficientMemory',1).replace('        case .premiumRequired: return "Для расшифровки через Telegram нужен Telegram Premium."\n','',1)
    assert s==before[settings],'Settings/defaults/provider/model registry changed'
    menu=current[MENU].replace(' && !NagramiXTranscriptionRuntime.handles(message, context: context) ?',' ?',1);assert menu==before[MENU],'Unrelated context-menu changes'
    rt=current[ASR+'Runtime.swift'];old=before[ASR+'Runtime.swift']
    for marker in ['    public static func canUseTelegram(','    public static func file(','    private static func identity(','    private static func valid(','    private static func load(','    private static func store(']:assert block(rt,marker)==block(old,marker),marker
    configuration=block(rt,'    private static func configuration(for message:')
    assert not re.search(r'configuration\.(?:provider|enabled)\s*=(?!=)',configuration),'Silent provider/master override returned'
    assert 'config.localFallback == true' in rt and '(index == 0 && !automatic) || NagramiXTranscriptionApple.authorized' in rt
    assert 'DispatchQueue.global(qos: .utility).asyncAfter(deadline: .now() + 120' in rt
    assert 'message.id.peerId.namespace != Namespaces.Peer.SecretChat' in block(rt,'    private static func canUseTelegramFile(')
    return {'inputs':4,'guards':18,'original_rpc_and_rating':'byte_identical','lifetime_storage_cache_identity':'byte_identical','secret_chat_cloud_export':'excluded','master_and_provider_overrides':'removed','new_ui_keys':0,'timeout_seconds':120}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='settings_section_header_case' and verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/n)==h,n
    contract=source_contract(a.source,plan);initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='premium-temporary-asr-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards');native=native_check(a.source,a.swiftc,folder/'native')
        text=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'premium-file-asr',text)
        for name,mutated,label in runtime.negatives(text):runs+=execute(a.swiftc,folder,name,mutated,label)
        for n in plan['inputs']:run([a.swiftc,'-frontend','-parse',a.source/n])
    assert manifest(a.source)==initial
    report={'stage':STAGE,'contract':contract,'loader_refusals':len(refused),'native_api':native,'executions':runs,'source_files':len(initial),'source_unchanged_by_checks':True,'whole_app_sdk':'not_run','telegram_server_acceptance':'not_tested','device':'pending','boundary':'Full production Settings/Runtime/Coordinator/Engine and unchanged original-ID guard execute with explicit IO/Postbox/network/TL-storage adapters. Actual native SwiftTL is rebuilt and the real generated file-RPC builder executes in the fixture. This proves request shape, routing, cancellation, lifetime and storage; it does not prove Telegram server availability, real speech quality or iPhone rendering.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
