#!/usr/bin/env python3
"""Check the actual PiP playback lifecycle and the guarded native integration."""
from __future__ import annotations
import argparse, ast, hashlib, importlib.util, json, shutil, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
V = 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
DRIVER = 'submodules/GalleryUI/Sources/NagramiXPiPPlaybackSession.swift'

def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def validate(before, after, swiftc):
    a, b = manifest(before), manifest(after)
    assert b.keys() - a.keys() == {DRIVER} and not a.keys() - b.keys()
    module_ast = ast.parse((ROOT/'ios/apply_features.py').read_text())
    fn = next(n for n in module_ast.body if isinstance(n, ast.FunctionDef) and n.name == 'apply_system_pip_playback_engine')
    assignments = {n.targets[0].id:n.value for n in fn.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    hashes, patches, templates = [ast.literal_eval(assignments[k]) for k in ['hashes','patches','templates']]
    changed = {n for n in a if a[n] != b[n]}
    localizations = {'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift', *[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['en','ru']]}
    assert changed == set(hashes) | localizations, changed
    assert hashes == {n:a[n] for n in hashes}
    replacements = {marker:(ROOT/'ios'/name).read_text().rstrip('\n') for marker,name in templates.items()}
    restored = {n:(after/n).read_text() for n in hashes}
    for name, old, new in reversed(patches):
        for marker,value in replacements.items(): new = new.replace(marker,value)
        assert restored[name].count(new)==1,(name,new[:80])
        restored[name]=restored[name].replace(new,old,1)
    start='@available(iOS 15.0, *)\nprivate final class NativePictureInPictureContentImpl:'
    end='final class UniversalVideoGalleryItemNode:'
    old=(before/V).read_text();old_adapter=old[old.index(start):old.index(end)]
    adapter=replacements['__SYSTEM_CONTENT__']+'\n\n'
    assert restored[V].count(adapter)==1
    restored[V]=restored[V].replace(adapter,old_adapter,1)
    assert all(restored[n].encode()==(before/n).read_bytes() for n in hashes)
    spec=importlib.util.spec_from_file_location('engine_overlay',ROOT/'ios/apply_features.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    guard_cases=[]
    with tempfile.TemporaryDirectory() as folder:
        native=Path(folder)/'native';overlay=Path(folder)/'ios'
        def seed():
            for path in [native,overlay]:
                if path.exists():shutil.rmtree(path)
            for n in hashes:
                p=native/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(before/n,p)
            for n in [*templates.values(),'Sources/GalleryUI/NagramiXPiPPlaybackSession.swift']:
                p=overlay/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'ios'/n,p)
        def reject(label):
            old=manifest(native)
            try:module.apply_system_pip_playback_engine(native,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(native)==old,label
            guard_cases.append(label)
        seed();module.apply_system_pip_playback_engine(native,overlay)
        assert all((native/n).read_bytes()==(after/n).read_bytes() for n in [*hashes,DRIVER])
        reject('reapply')
        for n in hashes:
            seed();p=native/n;p.write_bytes(p.read_bytes()+b'\n// drift');reject('drift '+n)
            seed();(native/n).unlink();reject('missing '+n)
        seed();p=native/DRIVER;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('collision');reject('collision')
        for n in [*templates.values(),'Sources/GalleryUI/NagramiXPiPPlaybackSession.swift']:
            seed();(overlay/n).unlink();reject('missing '+n)
    video=(after/V).read_text()
    assert video.count('private final class NativePictureInPictureContentImpl:')==1
    assert video.count('controller.startPictureInPicture()')==0  # only the injected backend closure uses optional chaining
    assert video.count('controller?.startPictureInPicture()')==1
    assert video.count('self.nagramiXStartSystemPiP(requiresSwipeSetting:')==2
    adapter=replacements['__SYSTEM_CONTENT__']
    will_start=adapter.split('func pictureInPictureControllerWillStartPictureInPicture',1)[1].split('func pictureInPictureControllerDidStartPictureInPicture',1)[0]
    assert 'willBegin' not in will_start and 'setCanPlaybackWithoutHierarchy' not in will_start
    assert 'AVPlayerLayer' in adapter and 'AVSampleBufferDisplayLayer' in adapter
    assert 'isPictureInPicturePossible, options: [.new]' in adapter
    assert 'self.audioReady &&' in adapter and '!self.audioSession.getIsRecordingActive()' in adapter
    assert 'getVideoLayer()' not in adapter and 'togglePlayPause' not in adapter
    assert 'completion(false)' in video and 'completion(true)' in video
    assert (after/DRIVER).read_bytes()==(ROOT/'ios/Sources/GalleryUI/NagramiXPiPPlaybackSession.swift').read_bytes()
    executed=[]
    with tempfile.TemporaryDirectory() as folder:
        for mode in ['debug','optimized']:
            args=[str(swiftc),'-module-cache-path',folder+'/cache','-warnings-as-errors',str(after/DRIVER),str(ROOT/'scripts/tests/NagramiXPiPPlaybackSessionTests.swift'),'-o',folder+'/test']
            if mode=='optimized':args.insert(1,'-O')
            subprocess.run(args,check=True);output=subprocess.check_output([folder+'/test'],text=True).strip();executed.append(mode+': '+output)
        # Syntax checks are explicitly distinct from Apple SDK typechecking.
        subprocess.run([str(swiftc),'-frontend','-parse',*[str(after/n) for n in hashes if n.endswith('.swift')]],check=True)
    return {'outputs':len(b),'changed':sorted(changed),'new':DRIVER,'unchanged':len(a)-len(changed),'reverse_patches':len(patches),'guard_cases':guard_cases,'lifecycle_execution':executed,'ios_native_compile':'pending','device':'pending'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path)
    args=p.parse_args();result=json.dumps(validate(args.before,args.after,args.swiftc),ensure_ascii=False,indent=2)+'\n'
    if args.report:args.report.write_text(result)
    print(result,end='')
