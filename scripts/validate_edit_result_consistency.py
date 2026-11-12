#!/usr/bin/env python3
"""Проверить локальный commit всех штатных контейнеров ответа редактирования."""
import argparse,json,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,digest,guard_checks
from validate_private_temporary_transcription import execute
from validate_local_copy_delivery import run
import edit_result_consistency_runtime as runtime

ROOT=Path(__file__).resolve().parents[1];STAGE='edit_result_consistency'

def source_contract(source,plan):
    assert plan['required_previous_stage']=='font_preview_apply' and set(plan['inputs'])=={runtime.EDIT} and len(plan['guards'])==8
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for n,h in {**plan['outputs'],**plan['guards']}.items():assert digest(source/n)==h,n
    before=(ROOT/'ios'/plan['previous'][runtime.EDIT]).read_text();after=(source/runtime.EDIT).read_text()
    old=block(before,'                            switch result {');lines=old.splitlines()
    assert lines[1].strip()=='case let .updates(updatesData):'
    new='                            let (updates, users, chats) = (result.allUpdates, result.users, result.chats)\n'+'\n'.join(line[4:] for line in lines[3:-3])
    assert before.replace(old,new,1)==after,'Изменён код вне распаковки контейнера; RPC/upload/error/metadata paths должны остаться прежними'
    util=(source/runtime.UTIL).read_text()
    for marker in ['    var allUpdates:','    var users: [Api.User] {','    var messages: [Api.Message] {','    var chats: [Api.Chat] {']:
        assert 'case let .updatesCombined(' in block(util,marker),marker
    assert 'case let .updateShort(' in block(util,'    var allUpdates:')
    assert after.count('stateManager.addUpdates(result)')==before.count('stateManager.addUpdates(result)')==1
    assert after.count('return .done(true)')==1
    state=(source/'submodules/TelegramCore/Sources/State/AccountStateManager.swift').read_text()
    assert 'self.queue.async' in block(state,'        func addUpdates(_ updates: Api.Updates) {')
    return {'only_change':'Native result.allUpdates/users/chats replace updates-only unwrapping; four existing per-message handlers are exact modulo indentation.','native_getters':'actual unchanged UpdatesApiUtils bodies used','request_upload_error_policy':'byte-for-byte unchanged outside this container block','pending_manager':'unchanged'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    plan=checked_plan(STAGE);contract=source_contract(a.source,plan);initial=manifest(a.source)
    with tempfile.TemporaryDirectory(prefix='edit-result-consistency-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards')
        code=runtime.fixture(a.source);runs=execute(a.swiftc,folder,'edit-result',code)
        runs+=execute(a.swiftc,folder,'published-regression',runtime.fixture(a.source,original=True),'accepted edit is stored before pending disappears')
        for name,mutated,label in runtime.negatives(code):runs+=execute(a.swiftc,folder,name,mutated,label)
        run([a.swiftc,'-frontend','-parse',a.source/runtime.EDIT])
    assert manifest(a.source)==initial
    report={'stage':STAGE,'inputs':1,'guards':8,'source_contract':contract,'loader_refusals':len(refused),'executions':runs,'swift_parse':1,'source_unchanged':True,'warnings_as_errors':True,'live_rpc':'not_run','whole_app_sdk':'not_run','device':'pending','boundary':'Actual full edit-result transaction, native API getters, ChatUpdatingMessageMedia and PendingUpdateMessageManagerImpl execute. Transport/Postbox/Signal queues and API payload storage are explicit deterministic adapters. Test suspends global update processing to reproduce old-text fallback. Video has no RPC/network log, so its exact response constructor and sole cause are unproven.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='executions'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
