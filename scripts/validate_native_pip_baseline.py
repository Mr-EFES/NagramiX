#!/usr/bin/env python3
"""Проверить штатный PiP Telegram13.1.2 и единую кнопку/быстрый свайп."""
import argparse,copy,hashlib,importlib.util,json,resource,subprocess,tempfile
from pathlib import Path
from validate_quick_format import block,manifest
ROOT=Path(__file__).resolve().parents[1];OVERLAY=ROOT/'ios';STAGE='native_pip_baseline'
PLAN=json.loads((OVERLAY/(STAGE+'_patches.json')).read_text())
U='submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
G='submodules/GalleryUI/Sources/GalleryController.swift'
N='submodules/GalleryUI/Sources/GalleryControllerNode.swift'
I='submodules/GalleryUI/Sources/GalleryItemNode.swift'
PIN='279f89e4d4f63f17227bf877dc3d8990f22ecd58'
NATIVE_BLOCKS=['private final class NativePictureInPictureContentImpl:',
 '    private func setupNativePictureInPicture()', '    @objc func pictureInPictureButtonPressed()',
 '    func expandPIP()', '    private func expandIntoCustomPiP()',
 '    override func centralityUpdated(isCentral:', '    override func visibilityUpdated(isVisible:',
 '    override func controlsVisibilityUpdated(isVisible:',
 'private final class UniversalVideoGalleryItemPictureInPictureNode:',
 '    private func updateDisplayPlaceholder(_ displayPlaceholder:',
 '    override func maybePerformActionForSwipeDownDismiss()']

def sha(data):return hashlib.sha256(data).hexdigest()
def native(name):return (OVERLAY/PLAN['native'][name]['source']).read_text()

def verify(source):
    for name,digest in {**PLAN['outputs'],**PLAN['guards']}.items():assert sha((source/name).read_bytes())==digest,name
    for name,digest in PLAN['templates'].items():assert sha((OVERLAY/name).read_bytes())==digest,name
    assert PIN in (OVERLAY/'upstream.env').read_text()
    assert set(PLAN['native'])==set(PLAN['outputs'])
    for name,item in PLAN['native'].items():assert PLAN['templates'][item['source']]==item['sha256']
    u=(source/U).read_text();p=native(U)
    for marker in NATIVE_BLOCKS:assert block(u,marker)==block(p,marker),marker
    assert u.count('private final class NativePictureInPictureContentImpl:')==1
    assert 'self.pictureInPictureButtonPressed()' in block(u,'    override func maybePerformActionForSwipeDismiss()')
    assert 'nativePictureInPicturePrepared' not in u and 'keepsVideoAttached' not in u
    assert 'KVO' not in block(u,'private final class NativePictureInPictureContentImpl:')
    node=(source/N).read_text();begin=node.index('// Shortcut admission only:');end=node.index('open class GalleryControllerNode:',begin)
    branch=block(node,'        if nagramiXShouldBeginFastPictureInPictureSwipe(')
    restored=node[:begin]+node[end:]
    restored=restored.replace(branch+'\n','')
    assert restored==native(N),'Native gallery node changed outside swipe admission'
    item=(source/I).read_text();prop=block(item,'    open var usesNativePictureInPictureSwipe:')
    assert item.replace(prop+'\n\n','')==native(I),'Native base item changed outside swipe capability'
    g=(source/G).read_text()
    for marker in ['    override public func viewDidAppear(', '    override public func containerLayoutUpdated(']:assert block(g,marker)==block(native(G),marker),marker
    assert 'nativePictureInPictureRestoreCompletion' not in g and 'prepareNativePictureInPictureTransition' not in g
    # Preserve independently approved content/privacy/background behavior.
    assert u.count('nagramiXUpdateBackgroundVideoPlayback()')==(OVERLAY/PLAN['previous'][U]).read_text().count('nagramiXUpdateBackgroundVideoPlayback()')
    assert g.count('nagramiXAllowsScreenshotBypass: message.nagramiXAllowsScreenshotBypass')==native(G).count('nagramiXAllowsScreenshotBypass: message.nagramiXAllowsScreenshotBypass')+5
    post=json.loads((OVERLAY/'upstream_13_2_post_patches.json').read_text());assert not set(PLAN['outputs'])&set(post['outputs'])
    pipeline=(OVERLAY/'apply_overlay.py').read_text();assert pipeline.index('    apply_copy_delivery(')<pipeline.index('    apply_native_pip_baseline(')
    return len(NATIVE_BLOCKS)+2


def guard_checks(source,temp):
    spec=importlib.util.spec_from_file_location(STAGE,OVERLAY/(STAGE+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    apply=module.apply_native_pip_baseline;rejected=[]
    def seed(label):
        tree=temp/label
        for n in {**PLAN['inputs'],**PLAN['guards']}:
            p=tree/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OVERLAY/PLAN['previous'][n] if n in PLAN['previous'] else source/n).read_bytes())
        return tree
    def reject(tree,label,overlay=OVERLAY):
        before=manifest(tree)
        try:apply(tree,overlay)
        except (SystemExit,OSError):pass
        else:raise AssertionError('Invalid input accepted: '+label)
        assert manifest(tree)==before,'Partial write: '+label
        rejected.append(label)
    valid=seed('valid');apply(valid,OVERLAY)
    for n in PLAN['outputs']:assert (valid/n).read_bytes()==(source/n).read_bytes(),n
    reject(valid,'repeat')
    for i,n in enumerate({**PLAN['inputs'],**PLAN['guards']}):
        for kind in ['missing','drift']:
            tree=seed(str(i)+kind)
            if kind=='missing':(tree/n).unlink()
            else:(tree/n).write_bytes(b'drift')
            reject(tree,kind+' '+n)
    f=next(iter(PLAN['inputs']));variants=[]
    for field in ['inputs','outputs','guards','templates']:
        bad=copy.deepcopy(PLAN);bad[field][next(iter(bad[field]))]='0'*64;variants.append((field,bad))
    for field in ['previous','replacements']:
        bad=copy.deepcopy(PLAN);bad[field][f]='../outside.swift';variants.append((field,bad))
    bad=copy.deepcopy(PLAN);bad['outputs'].clear();variants.append(('inconsistent',bad))
    for label,bad in variants:
        overlay=temp/('overlay-'+label)
        for n in PLAN['templates']:
            p=overlay/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((OVERLAY/n).read_bytes())
        (overlay/(STAGE+'_patches.json')).write_text(json.dumps(bad));reject(seed('source-'+label),label,overlay)
    for i,n in enumerate([f,next(iter(PLAN['guards']))]):
        tree=seed('symlink-'+str(i));p=tree/n;external=temp/('outside-'+str(i));external.write_bytes(p.read_bytes());p.unlink();p.symlink_to(external);reject(tree,'external symlink '+n)
    return rejected


def runtime(source):
    u=(source/U).read_text();node=(source/N).read_text()
    boundary=(ROOT/'scripts/tests/NagramiXNativePiPBaselineBoundary.swift').read_text()
    boundary=boundary.replace('// PRODUCTION_SCROLL',block(node,'    open func scrollViewWillEndDragging(').replace('open ',''))
    boundary=boundary.replace('// PRODUCTION_HELPER',block(node,'func nagramiXShouldBeginFastPictureInPictureSwipe('))
    controller=block(u,'private final class NativePictureInPictureContentImpl:').replace('private ','').replace('public ','')
    methods='\n'.join(block(u,m) for m in ['    private func setupNativePictureInPicture()', '    @objc func pictureInPictureButtonPressed()', '    func expandPIP()', '    override var usesNativePictureInPictureSwipe:', '    override func maybePerformActionForSwipeDismiss()', '    override func maybePerformActionForSwipeDownDismiss()'])
    methods=methods.replace('private ','').replace('@objc ','').replace('UniversalVideoGalleryItemNode','GalleryHarness')
    gallery='''
final class GalleryHarness:GalleryBase {
    let context=AccountContext();let footerContentNode=Footer();let gallery=GalleryController();let navigation=NavigationController()
    var item:Item?=Item();var videoNode:UniversalVideoNode?=UniversalVideoNode();var nativePictureInPictureContent:AnyObject?
    var activePictureInPictureController:BaseController?;var activePictureInPictureNavigationController:NavigationController?
    var isCentral:Bool?=true;var hasPictureInPicture=true;var settingsButtonState=0;var displayStickersButton=false;var dismissals=0
    func galleryController()->BaseController?{gallery}
    func baseNavigationController()->NavigationController?{navigation}
    func beginCustomDismiss(_ type:Dismiss) {}
    func completeCustomDismiss(_ active:Bool){dismissals+=1}
    func updateControlsVisibility(_ visible:Bool) {}
'''+methods+'\n}\n'
    return boundary+'\n'+controller+'\n'+gallery+'\n'+(ROOT/'scripts/tests/NagramiXNativePiPBaselineTests.swift').read_text()


def execute(source,swiftc,temp):
    code=runtime(source)
    variants={'current':code,
      'separate-swipe-entry':code.replace('        self.pictureInPictureButtonPressed()\n        return true','        self.setupNativePictureInPicture()\n        return true'),
      'old-long-gesture':code.replace('return distance >= 32.0 || velocity.y >= 0.35','return distance >= 160.0 || velocity.y >= 1.0'),
      'reversal-triggers-pip':code.replace('velocity.y >= 0.0 else','true else'),
      'ignored-swipe-setting':code.replace('guard NagramiXTabSettings.videoPiPSwipeEnabled, self.hasPictureInPicture,','guard true, self.hasPictureInPicture,'),
      'invisible-native-restore':code.replace('activePictureInPictureController.view.alpha = 1.0','activePictureInPictureController.view.alpha = 0.0'),
    }
    assert all(c!=code for name,c in variants.items() if name!='current')
    results=[]
    for label,content in variants.items():
        f=temp/(label+'.swift');f.write_text(content)
        for optimized in [False,True]:
            exe=temp/(label+('-O' if optimized else '-debug'))
            built=subprocess.run([str(swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),*(['-O'] if optimized else []),str(f),'-o',str(exe)],capture_output=True,text=True)
            assert built.returncode==0,built.stdout+built.stderr
            run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if label=='current':assert run.returncode==0,run.stdout+run.stderr;status=run.stdout.strip()
            else:assert run.returncode!=0 and 'Native PiP regression:' in run.stderr,run.stdout+run.stderr;status='regression reproduced and rejected'
            results.append(exe.name+': '+status);print(results[-1],flush=True)
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
    from validate_system_video_pip import delegate_icon_stage_if_applied
    if delegate_icon_stage_if_applied(a,Path(__file__),'pip_playback_commands'):return
    if delegate_icon_stage_if_applied(a,Path(__file__),'round_caption_transport'):return
    if delegate_icon_stage_if_applied(a,Path(__file__),'repost_copy_integrity'):return
    count=verify(a.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-native-pip-baseline-') as directory:
        temp=Path(directory);rejected=guard_checks(a.source,temp/'guards');run=temp/'runtime';run.mkdir();results=execute(a.source,a.swiftc,run) if a.swiftc else []
        if a.swiftc:
            for n in PLAN['outputs']:subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/n)],check=True)
    report={'replacements':len(PLAN['outputs']),'guards':len(PLAN['guards']),'pinned_native_blocks':count,'fail_closed':len(rejected),'executions':results,'source_pin':PIN,'sdk':'not authorized or run','device':'pending','boundaries':'Pinned native controller/playback delegate, setup, button, expand, swipe query/action, complete scroll release delegate. AVKit, UIKit, signal delivery, navigation and animation clock are explicit boundaries; no physical animation equivalence claimed.'}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
