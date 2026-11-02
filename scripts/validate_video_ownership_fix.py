#!/usr/bin/env python3
"""Проверить сохранение запроса воспроизведения до получения видеослоя."""
import argparse,copy,hashlib,importlib.util,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def plan():return json.loads((ROOT/'ios/video_ownership_fix_patches.json').read_text())
def is_applied(source):return all((source/n).is_file() and sha((source/n).read_bytes())==h for n,h in plan()['outputs'].items())
def delegate_if_applied(args):
    from validate_transcription_settings_refinement import delegate_if_applied as delegate_latest
    if delegate_latest(args): return True
    if not is_applied(args.source):return False
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--source',str(args.source),*(['--swiftc',str(args.swiftc)] if args.swiftc else [])],check=True)
    return True

def guards(source, p, temp):
    spec = importlib.util.spec_from_file_location('video_ownership_fix', ROOT / 'ios/video_ownership_fix.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    original = {n: (source / n).read_bytes() for n in p['guards']}; original.update(previous_bytes(p))
    rejected = []
    from validate_quick_format import manifest
    def seed():
        root = temp / 'source'
        for n, data in original.items():
            dest = root / n; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
        return root
    def reject(root, label, overlay=ROOT / 'ios'):
        before = manifest(root)
        try: module.apply_video_ownership_fix(root, overlay)
        except SystemExit: pass
        else: raise AssertionError('Принят неверный вход: ' + label)
        assert manifest(root) == before, 'Частичная запись: ' + label
        rejected.append(label); shutil.rmtree(root)
        if overlay != ROOT / 'ios': shutil.rmtree(overlay)
    def overlay(patch):
        root = temp / 'overlay'; root.mkdir()
        (root / 'video_ownership_fix_patches.json').write_text(json.dumps(patch))
        for n in p['templates']:
            dest = root / n; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((ROOT / 'ios' / n).read_bytes())
        return root
    for n in original:
        for mode in ['missing','drift']:
            root = seed(); path = root / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(root, mode + ' ' + n)
    for n in p['copies']:
        root = seed(); path = root / n; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('collision')
        reject(root, 'helper collision ' + n)
    for n in p['templates']:
        for mode in ['missing','drift']:
            root = seed(); bad = overlay(p); path = bad / n
            if mode == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes()+b'\n// drift')
            reject(root, mode + ' template ' + n, bad)
    for field in ['inputs','outputs','guards','templates']:
        if not p[field]: continue
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '0'*64
        reject(seed(),field + ' SHA',overlay(bad))
    for field in ['replacements','previous']:
        bad = copy.deepcopy(p); bad[field][next(iter(bad[field]))] = '../outside'
        reject(seed(),field+' traversal',overlay(bad))
    if p['copies']:
        bad = copy.deepcopy(p); entry = bad['copies'].pop(next(iter(bad['copies']))); bad['copies']['../outside'] = entry
        reject(seed(),'copy traversal',overlay(bad))
    root = seed(); module.apply_video_ownership_fix(root,ROOT/'ios'); reject(root,'repeat application')
    return rejected

def previous_bytes(p):
    result={n:(ROOT/'ios'/v).read_bytes() for n,v in p['previous'].items()}
    for n,b in result.items(): assert sha(b)==p['inputs'][n],n
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--swiftc',type=Path);args=parser.parse_args()
    from validate_transcription_settings_refinement import delegate_if_applied as delegate_latest
    if delegate_latest(args): return
    p=plan()
    item=next(iter(p['outputs']));before=previous_bytes(p)[item].decode();after=(args.source/item).read_text()
    assert sha(after.encode())==p['outputs'][item]
    assert after==before.replace('if strongSelf.playOnContentOwnership {','if value && strongSelf.playOnContentOwnership {',1)
    gesture='submodules/GalleryUI/Sources/NagramiXPiPGestureController.swift'
    assert sha((args.source/gesture).read_bytes())==p['outputs'][gesture]
    assert 'CGAffineTransform(translationX: 0.0, y: offset)' in (args.source/gesture).read_text()
    lifecycle='submodules/GalleryUI/Sources/NagramiXPiPLifecycle.swift'
    assert sha((args.source/lifecycle).read_bytes())==p['outputs'][lifecycle]
    assert 'self.deadline = self.now() + self.startTimeout\n                self.phase = .starting' in (args.source/lifecycle).read_text()
    with tempfile.TemporaryDirectory(prefix='nagramix-ownership-') as folder:
        temp=Path(folder);rejected=guards(args.source,p,temp);names=set(p['inputs'])
        if args.swiftc:
            from validate_pip_native_entry import compile_run
            support=(ROOT/'scripts/tests/NagramiXPiPGestureSupport.swift').read_text().replace('    var prepareCount = 0, startCount = 0, cancelCount = 0','    var failureCount = 0\n    func nagramiXPictureInPictureRequestFailed() { failureCount += 1 }\n    var prepareCount = 0, startCount = 0, cancelCount = 0')
            support_path=temp/'GestureSupport.swift';support_path.write_text(support)
            code=(args.source/gesture).read_text().replace('import UIKit\n','import Foundation\n').replace('import Display\n','').replace('@objc private func pan(','private func pan(').replace('#selector(self.pan(_:))','0')
            gesture_path=temp/'Gesture.swift';gesture_path.write_text(code+'\nextension NagramiXPiPGestureController { func testDrivePan() { self.pan(self.recognizer) } }\n')
            tests=ROOT/'scripts/tests/NagramiXPiPInteractiveGestureTests.swift'
            for optimized in [False,True]:
                compile_run(args.swiftc,temp,'interactive-'+str(optimized),[support_path,ROOT/'ios/Sources/GalleryUI/NagramiXPiPReleaseDecision.swift',gesture_path,tests],optimized=optimized)

        for file in (ROOT/'ios').glob('*_patches.json'):
            old=json.loads(file.read_text())
            for field in ['inputs','outputs','guards','copies']:names.update(old.get(field,{}))
        names.add('Telegram/Telegram-iOS/en.lproj/Localizable.strings');prior=temp/'prior'
        for n in names:
            src=args.source/n
            if not src.is_file():continue
            path=prior/n;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(previous_bytes(p)[n] if n in p['inputs'] else src.read_bytes())
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_release_076_import.py'),'--source',str(prior)],check=True)
    print('PASS: воспроизведение ожидает получения видеослоя; guards:',len(rejected))
if __name__=='__main__':main()
