#!/usr/bin/env python3
"""Проверить прямой вход PiP, реальный WindowHost и видимый source до didStart."""
import argparse, ast, copy, hashlib, importlib.util, json, os, resource, shutil, subprocess, sys, tempfile
from pathlib import Path
from validate_quick_format import block, manifest

ROOT=Path(__file__).resolve().parents[1]
G='submodules/GalleryUI/Sources/'
ITEM=G+'Items/UniversalVideoGalleryItem.swift';NODE=G+'GalleryControllerNode.swift';API=G+'GalleryItemNode.swift'
FOOTER=G+'ChatItemGalleryFooterContentNode.swift';GESTURE=G+'NagramiXPiPGestureController.swift';TRACE=G+'NagramiXPiPDiagnostics.swift'
WINDOW='submodules/Display/Source/WindowContent.swift'

def sha(data):return hashlib.sha256(data).hexdigest()
def plan():return json.loads((ROOT/'ios/pip_native_entry_patches.json').read_text())
def is_applied(source):return all((source/n).is_file() and sha((source/n).read_bytes())==h for n,h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_release_076_compile import delegate_if_applied as delegate_compile
    if delegate_compile(args): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    return True

def reverse(source,p):
    result={n:(source/n).read_bytes() for n in p['inputs']}
    for n,a,b,count in reversed(p['patches']):
        text=result[n].decode();assert text.count(b)==count,n;result[n]=text.replace(b,a,count).encode()
    for n,data in result.items():assert sha(data)==p['inputs'][n],n
    return result

def guards(source,p,previous,temp):
    spec=importlib.util.spec_from_file_location('pip_native_entry',ROOT/'ios/pip_native_entry.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    original={**{n:(source/n).read_bytes() for n in p['guards']},**previous};rejected=[]
    def seed(label):
        root=temp/label
        for n,data in original.items():path=root/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return root
    def overlay_for(label,value):
        root=temp/('plan-'+label);root.mkdir();(root/'pip_native_entry_patches.json').write_text(json.dumps(value))
        for n in p['templates']:
            path=root/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/'ios'/n).read_bytes())
        return root
    def reject(root,label,overlay=ROOT/'ios'):
        before=manifest(root)
        try:mod.apply_pip_native_entry(root,overlay)
        except SystemExit:pass
        else:raise AssertionError('Принят некорректный вход: '+label)
        assert manifest(root)==before,'Частичная запись: '+label
        rejected.append(label);shutil.rmtree(root)
        if overlay!=ROOT/'ios':shutil.rmtree(overlay)
    good=seed('good');mod.apply_pip_native_entry(good,ROOT/'ios')
    assert all((good/n).read_bytes()==(source/n).read_bytes() for n in {*original,*p['copies']})
    reject(good,'reapply')
    for n in original:
        for mode in ['missing','drift']:
            root=seed('root-'+str(len(rejected)));path=root/n
            if mode=='missing':path.unlink()
            else:path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(root,mode+' '+n)
    for n in p['templates']:
        for mode in ['missing','drift']:
            label='template-'+str(len(rejected));overlay=overlay_for(label,p);path=overlay/n
            if mode=='missing':path.unlink()
            else:path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(seed('root-'+label),mode+' '+n,overlay)
    root=seed('collision');path=root/TRACE;path.write_text('collision');reject(root,'helper collision')
    mutations=[]
    for i in range(len(p['patches'])):
        value=copy.deepcopy(p);value['patches'][i][1]+=' bad';mutations.append(('anchor-'+str(i),value))
    for field in ['inputs','outputs','guards']:
        value=copy.deepcopy(p);value[field][next(iter(value[field]))]='0'*64;mutations.append((field+'-sha',value))
    value=copy.deepcopy(p);value['copies'][TRACE]['sha256']='0'*64;mutations.append(('helper-sha',value))
    value=copy.deepcopy(p);value['inputs']['../outside']='0'*64;value['outputs']['../outside']='0'*64;mutations.append(('traversal',value))
    for label,value in mutations:reject(seed('root-'+label),label,overlay_for(label,value))
    return rejected

def prior_checks(source,p,previous,temp,swiftc):
    names=set(p['inputs'])|set(p['guards'])
    for stage in ['pip_presentation','pip_native_transaction']:
        old=json.loads((ROOT/'ios'/(stage+'_patches.json')).read_text())
        for field in ['inputs','outputs','guards','copies']:names.update(old[field])
    root=temp/'prior'
    for n in names:
        path=root/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(previous[n] if n in previous else (source/n).read_bytes())
    subprocess.run([sys.executable,str(ROOT/'scripts/validate_pip_presentation.py'),'--source',str(root)],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/validate_pip_native_transaction.py'),'--source',str(root),*(['--swiftc',str(swiftc)] if swiftc else [])],check=True)

def closure_body(text,marker):
    code=block(text,marker)
    return code.split(' in\n',1)[1].rsplit('}',1)[0]

def prefix_for(source):
    item=(source/ITEM).read_text();setup=block(item,'private func setupNativePictureInPicture()')
    admission=item[item.index('private var nagramiXPiPCurrentGallery:'):item.index('    private func nagramiXStartSystemPiP(')]
    bind=item[item.index('        self.footerContentNode.nagramiXPictureInPictureRequested ='):item.index('        self.alternativeDismiss =')]
    data=(ROOT/'scripts/tests/NagramiXPiPNativeEntryBoundary.swift').read_text()
    window=(source/WINDOW).read_text()
    replacements={
        '// WINDOW_HOST_DECLARATION':block(window,'public protocol WindowHost {').replace('public ',''),
        '// WINDOW_HOST_GETTER':block(window,'var windowHost: WindowHost? {'),
        '// BACKDROP_METHOD':block((source/NODE).read_text(),'func nagramiXSetPiPBackdrop('),
        '// BIND_FOOTER':bind,
        '// ADMISSION_METHODS':admission,
        '// FADE_OUT_BODY':closure_body(setup,'fadeOut: {'),
        '// FADE_IN_BODY':closure_body(setup,'fadeIn: {'),
        '// TRANSFER_BODY':closure_body(setup,'transfer: {'),
        '// RESTORE_BODY':closure_body(setup,'restore: {'),
        '// FOOTER_METHOD':block((source/FOOTER).read_text(),'private func pipButtonPressed()'),
    }
    for marker,value in replacements.items():assert data.count(marker)==1,marker;data=data.replace(marker,value)
    trace=(source/TRACE).read_text().replace('import TelegramCore\n','')
    return data+'\n'+trace,admission,setup

def compile_run(swiftc,temp,label,files,failure=None,optimized=False):
    binary=temp/label
    subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),*map(str,files),'-o',str(binary)],check=True)
    result=subprocess.run([str(binary)],env=dict(os.environ,XDG_CONFIG_HOME=str(temp/(label+'-prefs'))),text=True,capture_output=True,timeout=45,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
    if failure:
        assert result.returncode!=0 and failure in result.stderr,result.stdout+result.stderr
        output=label+': прежний silent entry/source fade воспроизведён и отвергнут'
    else:
        assert result.returncode==0,result.stdout+result.stderr;output=label+': '+result.stdout.strip()
    print(output,flush=True);return output

def swift_tests(source,previous,swiftc,temp):
    prefix,admission,setup=prefix_for(source);olditem=previous[ITEM].decode();oldsetup=block(olditem,'private func setupNativePictureInPicture()')
    oldadmission=block(olditem,'private var nagramiXCanUseSystemPiP:')+'\n'+block((source/ITEM).read_text(),'private var nagramiXPiPCurrentGallery:')+'\nprivate var nagramiXPiPUnavailableReason: String? { nil }\n'
    variants=[('entry',prefix,None),('old-admission',prefix.replace(admission,oldadmission),'visible current gallery with a window host must be eligible without navigation'),
              ('old-footer',prefix.replace(block((source/FOOTER).read_text(),'private func pipButtonPressed()'),block(previous[FOOTER].decode(),'private func pipButtonPressed()')),'bound footer button must work before controller interaction is supplied'),
              ('old-fade',prefix.replace(closure_body(setup,'fadeOut: {'),closure_body(oldsetup,'fadeOut: {')),'willStart keeps live source visible')]
    tests=ROOT/'scripts/tests/NagramiXPiPNativeEntryTests.swift';visual=source/(G+'NagramiXPiPVisualHandoff.swift');runs=[]
    gesture=(source/GESTURE).read_text().replace('import UIKit\n','import Foundation\n').replace('import Display\n','').replace('@objc private func pan(','private func pan(').replace('#selector(self.pan(_:))','0')
    gesture+='\nextension NagramiXPiPGestureController { func testDrivePan() { self.pan(self.recognizer) } }\n'
    gesture_path=temp/'Gesture.swift';gesture_path.write_text(gesture)
    gesture_tests=temp/'GestureTests.swift'
    gesture_tests.write_text((ROOT/'scripts/tests/NagramiXPiPNativeGestureTests.swift').read_text().replace('@main struct', 'struct'))
    old_gesture=temp/'OldGesture.swift'
    old_gesture.write_text(previous[GESTURE].decode().replace('import UIKit\n','import Foundation\n').replace('import Display\n','').replace('@objc private func pan(','private func pan(').replace('#selector(self.pan(_:))','0')+'\nextension NagramiXPiPGestureController { func testDrivePan() { self.pan(self.recognizer) } }\n')
    support=(ROOT/'scripts/tests/NagramiXPiPGestureSupport.swift').read_text().replace('    var prepareCount = 0, startCount = 0, cancelCount = 0','    var failureCount = 0\n    func nagramiXPictureInPictureRequestFailed() { failureCount += 1 }\n    var prepareCount = 0, startCount = 0, cancelCount = 0')
    support_path=temp/'GestureSupport.swift';support_path.write_text(support)
    for optimized in [False,True]:
        suffix='-O' if optimized else '-debug'
        for name,code,failure in variants:
            path=temp/(name+'.swift');path.write_text(code)
            runs.append(compile_run(swiftc,temp,name+suffix,[path,visual,tests],failure,optimized))
        gesture_suite=[support_path,ROOT/'ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift',gesture_tests,ROOT/'scripts/tests/NagramiXPiPEntryGestureTests.swift']
        runs.append(compile_run(swiftc,temp,'gesture'+suffix,[*gesture_suite,gesture_path],optimized=optimized))
        runs.append(compile_run(swiftc,temp,'old-gesture'+suffix,[*gesture_suite,old_gesture],failure='rejected swipe reports once; successful swipe stays silent',optimized=optimized))
    subprocess.run([str(swiftc),'-frontend','-parse',*[str(source/n) for n in [*plan()['outputs'],TRACE]]],check=True)
    return runs

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    from validate_release_076_compile import delegate_if_applied as delegate_compile
    if delegate_compile(args): return
    p=plan()
    for n,h in {**p['guards'],**p['outputs']}.items():assert sha((args.source/n).read_bytes())==h,n
    for n,v in p['copies'].items():assert sha((args.source/n).read_bytes())==v['sha256'],n
    for n,h in p['templates'].items():assert sha((ROOT/'ios'/n).read_bytes())==h,n
    item=(args.source/ITEM).read_text();setup=block(item,'private func setupNativePictureInPicture()')
    assert 'controller.view.alpha = 0.0' not in setup and 'nagramiXSetPiPBackdrop(visible: false' in setup
    assert 'self.baseNavigationController() != nil' not in block(item,'private var nagramiXPiPUnavailableReason:')
    assert 'guard self.lifecycle.phase == .preparing else { return }' in item and item.count('startPictureInPicture()')==1
    assert 'UIImage' not in (args.source/TRACE).read_text() and 'nagramiXPictureInPictureRequested' in item
    calls=[n.func.id for n in ast.walk(ast.parse((ROOT/'ios/apply_overlay.py').read_text())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
    assert calls.index('apply_round_video_bitrate')<calls.index('apply_pip_native_entry')
    with tempfile.TemporaryDirectory(prefix='nagramix-pip-entry-') as folder:
        temp=Path(folder);previous=reverse(args.source,p);rejected=guards(args.source,p,previous,temp);prior_checks(args.source,p,previous,temp,args.swiftc)
        runs=swift_tests(args.source,previous,args.swiftc,temp) if args.swiftc else []
    result=dict(files=len(p['outputs']),helper=1,operations=len(p['patches']),guards=len(p['guards']),fail_closed=rejected,runs=runs,
                prior_contracts='точное восстановление предыдущих SHA и прежние native transaction/presentation проверки',
                limits='UIKit/AVKit/WindowHost delivery boundaries; root alpha/source ownership tested, actual AVKit device start not executed',
                physical_134_failure='точная причина на iPhone не установлена',SDK='не запускалась',device='ожидается')
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
