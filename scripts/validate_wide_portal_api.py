#!/usr/bin/env python3
"""Reject old wide-post wallpaper calls against the actual pinned native protocol."""
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_upstream_13_2_release import checked_plan,digest,guard_checks,OVERLAY
from validate_quick_format import manifest,block
from validate_private_temporary_transcription import execute
import wide_portal_api_runtime as runtime
from validate_feature_contract_consistency import negatives

STAGE='wide_portal_api'


def native_api_check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True)
    code=runtime.fixture(source);plan=checked_plan(STAGE)
    for name,expected in plan['native_guards'].items():
        data=(source/name).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected,name
    before=(OVERLAY/plan['previous'][runtime.VIEW]).read_text()
    original=runtime.original(source,code,before)
    flags=[]
    if sys.platform=='darwin':
        sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip();flags=['-sdk',sdk,'-target','arm64-apple-ios15.0']
    command=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-module-cache-path',str(folder/'cache'),*flags,'-typecheck']
    path=folder/'portal-api.swift';path.write_text(code)
    good=subprocess.run(command+[str(path)],capture_output=True,text=True,timeout=180);assert good.returncode==0,good.stdout+good.stderr
    path.write_text(original);bad=subprocess.run(command+[str(path)],capture_output=True,text=True,timeout=180)
    assert bad.returncode!=0 and "has no member 'update'" in bad.stderr,bad.stdout+bad.stderr
    return {'actual_pinned_protocol':'verbatim, including public access; native ASDisplayNode/theme edges adapted','actual_native_backdrop_frame_method':'verbatim','fixed_typecheck':'passed','original212_rejected':'has no member update','apple_iphoneos':('passed arm64/iOS15 typecheck' if sys.platform=='darwin' else 'not_run: Linux Foundation typecheck only'),'full_application_sdk':'pending','device':'pending'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args();plan=checked_plan(STAGE)
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,h in {**plan['outputs'],**plan['guards']}.items():assert digest(a.source/name)==h,name
    for name,blob in plan['native_guards'].items():
        data=(a.source/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob
    for name in plan['inputs']:assert 'updateNagramiXWidePostAbsoluteRect' not in (a.source/name).read_text()
    state=manifest(a.source);code=runtime.fixture(a.source)
    with tempfile.TemporaryDirectory(prefix='wide-portal-api-') as d:
        root=Path(d);refused=guard_checks(a.source,STAGE,plan,root/'guards');api=native_api_check(a.source,a.swiftc,root/'api')
        runs=execute(a.swiftc,root,'native-portal-frame',code)
        for name,changed,diagnostic in negatives('wide',code):
            # Wide envelope checks use the established exit91 convention.
            from validate_local_copy_delivery import execute as wide_execute
            runs+=wide_execute(a.swiftc,root,name,changed,diagnostic)
    assert manifest(a.source)==state
    report={'stage':STAGE,'loader_refusals':len(refused),'executions':runs,'native_api':api,'scope':'Only obsolete absolute-position cache/helper and its2callers removed. Native backdrop updateFrame owns local portal/mask bounds; no portal reload on scrolling. All artwork, envelope geometry, theme, selection and unrelated media/recording paths preserved.','full_application_sdk':'pending','device':'pending'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
