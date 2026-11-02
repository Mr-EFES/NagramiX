#!/usr/bin/env python3
"""Validate profile-story ownership and opt-in saving; no UIKit/Photos execution."""
import argparse, ast, hashlib, importlib.util, json, os, shutil, subprocess, tempfile
from pathlib import Path
from validate_quick_format import block
from validate_contact_chat_readiness import NATIVE, KIT

ROOT = Path(__file__).resolve().parents[1]
SCREEN = 'submodules/TelegramUI/Components/Stories/StoryContainerScreen/Sources/StoryContainerScreen.swift'
VIEW = 'submodules/TelegramUI/Components/Stories/StoryContainerScreen/Sources/StoryItemSetContainerComponent.swift'
SETTINGS = 'submodules/SettingsUI/Sources/NagramiXSettingsController.swift'


def run(args):
    plan = json.loads((ROOT/'ios/story_profile_patches.json').read_text())
    for group in ['inputs','guards']:
        for name, sha in plan[group].items():
            assert hashlib.sha256((args.before/name).read_bytes()).hexdigest()==sha
    for name,sha in plan['outputs'].items():
        assert hashlib.sha256((args.after/name).read_bytes()).hexdigest()==sha
    # Read approval, navigation, anonymous transport and native save menu stay intact.
    old, new = (args.before/SCREEN).read_text(), (args.after/SCREEN).read_text()
    for marker in ['fileprivate func nagramiXCanMarkStoryAsSeen(', 'fileprivate func nagramiXConfirmNavigation(', 'private func nagramiXUsesAnonymousViewing(']:
        assert block(old, marker)==block(new, marker)
    a,b=(args.before/VIEW).read_text(),(args.after/VIEW).read_text()
    assert block(a,'private func requestSave(')==block(b,'private func requestSave(')
    assert 'let reference: AnyMediaReference = .story(' in b
    assert 'guard !item.isForwardingDisabled ||' in b
    settings=(args.after/SETTINGS).read_text()
    assert settings.count('case .downloadStories: return 159')==1
    assert 'case .downloadStories: return 285' in settings
    assert '.downloadStories(NagramiXStoryDownloadSettings.enabled)' in settings
    spec=importlib.util.spec_from_file_location('story_profile', ROOT/'ios/story_profile.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    failures=[];execution=[]
    with tempfile.TemporaryDirectory(prefix='story-profile-') as folder:
        tmp=Path(folder)
        def seed(target):
            for name in {**plan['inputs'],**plan['guards']}:
                p=target/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/name,p)
        def snapshot(target):
            return {str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()}
        def reject(target,label,overlay=ROOT/'ios'):
            saved=snapshot(target)
            try: module.apply_story_profile(target,overlay)
            except SystemExit: pass
            else: raise AssertionError(label)
            assert snapshot(target)==saved,label
            failures.append(label)
        valid=tmp/'valid';seed(valid);module.apply_story_profile(valid,ROOT/'ios')
        for name in list(plan['outputs'])+list(plan['copies']): assert (valid/name).read_bytes()==(args.after/name).read_bytes()
        reject(valid,'reapply')
        for i,name in enumerate({**plan['inputs'],**plan['guards']}):
            for kind in ['missing','drift']:
                target=tmp/(kind+str(i));seed(target)
                if kind=='missing': (target/name).unlink()
                else: (target/name).write_bytes((target/name).read_bytes()+b'// drift')
                reject(target,kind+' '+name)
        for kind in ['anchor','output','unsafe']:
            target=tmp/kind;seed(target);overlay=tmp/(kind+'-overlay');shutil.copytree(ROOT/'ios',overlay,ignore=shutil.ignore_patterns('branding','Assets','Resources','__pycache__'))
            custom=json.loads(json.dumps(plan))
            if kind=='anchor': custom['patches'][-1]['old']+='// invalid'
            elif kind=='output': custom['outputs'][next(iter(custom['outputs']))]='0'*64
            else: custom['inputs']['../outside.swift']='0'*64
            (overlay/'story_profile_patches.json').write_text(json.dumps(custom));reject(target,kind,overlay)
        for i,(name,entry) in enumerate(plan['copies'].items()):
            for kind in ['collision','missing-helper','changed-helper']:
                target=tmp/(kind+str(i));seed(target)
                if kind=='collision':
                    p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('// owned')
                    reject(target,kind+' '+name)
                else:
                    overlay=tmp/(kind+str(i)+'-overlay');overlay.mkdir()
                    (overlay/'story_profile_patches.json').write_text(json.dumps(plan))
                    for template_name in plan['templates']:
                        p=overlay/template_name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/template_name,p)
                    for item in plan['copies'].values():
                        p=overlay/item['source'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/item['source'],p)
                    if kind=='missing-helper': (overlay/entry['source']).unlink()
                    else: (overlay/entry['source']).write_text('// altered')
                    reject(target,kind+' '+name,overlay)
        for index,template_name in enumerate(plan['templates']):
            for kind in ['missing-template','changed-template']:
                target=tmp/(kind+str(index));seed(target)
                overlay=tmp/(kind+str(index)+'-overlay')
                shutil.copytree(ROOT/'ios',overlay,ignore=shutil.ignore_patterns('branding','Assets','Resources','__pycache__'))
                if kind=='missing-template':(overlay/template_name).unlink()
                else:(overlay/template_name).write_text('// altered')
                reject(target,kind+' '+template_name,overlay)
        signal=[]
        for name in NATIVE:
            value=(args.upstream/(KIT+name)).read_text()
            if name=='Signal_Meta.swift': value='import CoreFoundation\n'+value
            p=tmp/name;p.write_text(value);signal.append(p)
        timing=(args.upstream/(KIT+'Signal_Timing.swift')).read_text()
        p=tmp/'Timing.swift';p.write_text('import Foundation\n'+block(timing,'public func timeout<'));signal.append(p)
        boundary=(ROOT/'scripts/tests/NagramiXStoryProfileBoundary.swift').read_text()
        def production(text):
            start=text.index('public func nagramiXPush(from parentController:')
            brace=text.index(') {',start)+2
            depth=1
            for end in range(brace+1,len(text)):
                if text[end]=='{': depth+=1
                elif text[end]=='}': depth-=1
                if depth==0: break
            push=text[start:end+1]
            result='\n'.join(block(text,marker) for marker in ['private func nagramiXUsesAnonymousViewing(', 'fileprivate func nagramiXCanMarkStoryAsSeen(', 'public func nagramiXPresent('])+'\n'+push
            return result.replace('public func ','func ').replace('fileprivate func ','func ').replace('private func ','func ')
        save=(ROOT/'ios/Sources/SaveToCameraRoll/NagramiXStorySave.swift').read_text()
        save='\n'.join(line for line in save.splitlines() if not line.startswith('import ') or line=='import Foundation')
        prefs=ROOT/'ios/Sources/NagramiXCore/Sources/NagramiXStoryDownloadSettings.swift'
        for mode in ['debug','optimized']:
            for version,text in [('baseline',old),('fixed',new)]:
                target=tmp/(version+mode+'.swift');target.write_text(boundary.replace('// NATIVE_PRESENTATION_METHODS',production(text)))
                sp=tmp/'Save.swift';sp.write_text(save)
                binary=tmp/(version+mode)
                cmd=[str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(tmp/'cache'),*map(str,signal),str(target),str(sp),str(prefs),str(ROOT/'scripts/tests/NagramiXStoryProfileTests.swift'),'-o',str(binary)]
                if mode=='optimized':cmd.insert(1,'-O')
                subprocess.run(cmd,check=True)
                env=dict(os.environ,XDG_CONFIG_HOME=str(tmp/(version+mode+'-prefs')))
                output=subprocess.check_output([str(binary)]+(['baseline'] if version=='baseline' else []),text=True,env=env,timeout=30)
                execution.append(version+'/'+mode+': '+output.strip())
                if version=='fixed':
                    for command,value in [('fresh','false'),('set','true'),('read','true'),('set','false'),('read','false'),('read','false')]:
                        subprocess.run([str(binary),command,value],env=env,check=True,timeout=15)
                    execution.append(mode+': six cold preference processes PASS')
        swift=[str(args.after/n) for n in list(plan['outputs'])+list(plan['copies']) if n.endswith('.swift')]
        subprocess.run([str(args.swiftc),'-frontend','-parse',*swift],check=True)
    return dict(inputs=len(plan['inputs']),build_guards=len(plan['guards']),operations=len(plan['patches']),helpers=len(plan['copies']),fail_closed=failures,execution=execution,Apple_SDK='pending',UIKit_Photos='boundaries only',iPhone='pending')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['before','after','upstream','swiftc','report']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=run(args);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
