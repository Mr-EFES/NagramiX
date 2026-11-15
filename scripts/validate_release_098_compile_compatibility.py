#!/usr/bin/env python3
"""Verify both native218 compiler failures and the smallest source-only fix."""
import argparse,json,tempfile
from pathlib import Path
from validate_quick_format import manifest,block
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from release_098_compile_contract import H,S,Q,check
STAGE='release_098_compile_compatibility'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);args=p.parse_args()
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='youtube_background_continuity'
    assert set(plan['inputs'])=={H,S} and len(plan['guards'])==11 and not plan['copies'] and not plan['deletions']
    assert verified_prefix(args.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,old,new in [(H,'configuration(accountId: self.context.account.id.int64).provider.title','configuration(accountId: context.account.id.int64).provider.title'),(S,'        private func endCaptionEditing() -> Bool {','        func endCaptionEditing() -> Bool {')]:
        before=(OVERLAY/plan['previous'][name]).read_text();after=(args.source/name).read_text()
        assert before.count(old)==1 and before.replace(old,new,1)==after,'Unrelated behavior changed: '+name
    # Scope only: caption commit, length veto, observers and layout are identical.
    before=(OVERLAY/plan['previous'][S]).read_text();after=(args.source/S).read_text()
    assert block(before,'        private func endCaptionEditing(').replace('private func','func',1)==block(after,'        func endCaptionEditing(')
    assert block(before,'        private func updateIsEditingCaption(')==block(after,'        private func updateIsEditingCaption(')
    state=manifest(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-098-compile-') as d:
        folder=Path(d);refused=guard_checks(args.source,STAGE,plan,folder/'guards');result=check(args.source,args.swiftc,folder/'cross-file')
    assert manifest(args.source)==state,'Validation modified application source'
    report={'stage':92,'name':STAGE,'runtime_paths':[H,S],'guards':11,'loader_refusals':len(refused),'cross_file_compilation':result,'unchanged_quality_caller':Q,'source_unchanged_by_checks':True,'changes':'Use existing strong local account context inside weak-self map; expose caption gate only within its existing Swift component module. No body/keys/resources/dependency/signing changes.','full_application_sdk':'pending','physical_iphone':'pending'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
