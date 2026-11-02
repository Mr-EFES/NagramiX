#!/usr/bin/env python3
"""Verify the selected-quality save fix without an Apple SDK build."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
def manifest(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def validate(before,after,swiftc):
    plan=json.loads((ROOT/'ios/video_quality_save_patches.json').read_text());a,b=manifest(before),manifest(after)
    changed={n for n in a if a[n]!=b.get(n)}
    expected={p[0] for p in plan['patches']}|{'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',*[f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings' for lang in ['ru','en']]}
    assert changed==expected,(changed^expected)
    assert b.keys()-a.keys()==set(plan['copies'].values()) and not a.keys()-b.keys()
    texts={n:(before/n).read_text() for n in plan['hashes']};assert all(a[n]==sha for n,sha in plan['hashes'].items())
    for n,old,new,count in plan['patches']:
        assert texts[n].count(old)==count;texts[n]=texts[n].replace(old,new,count)
    assert all((after/n).read_bytes()==v.encode() for n,v in texts.items())
    for src,n in plan['copies'].items():assert (after/n).read_bytes()==(ROOT/'ios'/src).read_bytes()
    spec=importlib.util.spec_from_file_location('video_save',ROOT/'ios/video_quality_save.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        def seed(p):
            for n in plan['hashes']:
                t=p/n;t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(before/n,t)
            for n in plan['copies'].values():(p/n).parent.mkdir(parents=True,exist_ok=True)
        def reject(p,label,overlay=ROOT/'ios'):
            old=manifest(p)
            try:module.apply_video_quality_save(p,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(p)==old,'partial write '+label
            rejected.append(label)
        p=root/'valid';seed(p);module.apply_video_quality_save(p,ROOT/'ios');assert all((p/n).read_bytes()==(after/n).read_bytes() for n in plan['hashes']);reject(p,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                p=root/(kind+str(i));seed(p)
                if kind=='missing':(p/n).unlink()
                else:(p/n).write_bytes((p/n).read_bytes()+b'\n// drift\n')
                reject(p,kind+' '+n)
        for i,(src,n) in enumerate(plan['copies'].items()):
            p=root/('collision'+str(i));seed(p);(p/n).write_text('// collision');reject(p,'collision '+n)
            p=root/('template'+str(i));seed(p);overlay=root/('overlay'+str(i));overlay.mkdir();shutil.copy2(ROOT/'ios/video_quality_save_patches.json',overlay)
            for s in plan['copies']:
                if s!=src:
                    q=overlay/s;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'ios'/s,q)
            reject(p,'missing template '+src,overlay)
        # Check missing destination parent even where another template shares it.
        p=root/'parent';seed(p);shutil.rmtree(p/'submodules/SaveToCameraRoll/Sources');reject(p,'missing helper parent')
    execution=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);sources=[]
        for i,n in enumerate(plan['copies'].values()):
            p=root/f'Production{i}.swift';source=(after/n).read_text();p.write_text('import Foundation\n'+'\n'.join(l for l in source.splitlines() if not l.startswith('import ')).replace('public ','').replace('SwiftSignalKit.Timer','MockTimer')+'\n');sources.append(p)
        for mode in ['debug','optimized']:
            binary=root/('test-'+mode);cmd=[str(swiftc),'-warnings-as-errors','-module-cache-path',str(root/'cache'),*map(str,sources),str(ROOT/'scripts/tests/NagramiXVideoSaveBoundary.swift'),str(ROOT/'scripts/tests/NagramiXVideoQualitySaveTests.swift'),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True);execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,timeout=40).strip())
        subprocess.run([str(swiftc),'-frontend','-parse',*[str(after/n) for n in changed|set(plan['copies'].values()) if n.endswith('.swift')]],check=True)
    gallery=(after/'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift').read_text()
    assert 'source: qualityFile, original: content.fileReference, quality: quality' in gallery
    assert 'case .permissionDenied: return' in gallery and 'case .library: key = "LibraryFailed"' in gallery
    assert 'mediaReference: qualityFile.abstract)\n                                            |> castError' in gallery
    assert '!message.isCopyProtected() && !item.peerIsCopyProtected && message.paidContent == nil' in gallery
    for lang in ['ru','en']:
        s=(after/f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        for key in ['FromOriginal','DownloadFailed','ConversionFailed','LibraryFailed']:assert s.count('"NagramiX.Video.Save.'+key+'" = ')==1
    return {'outputs':len(b),'changed':sorted(changed),'added':sorted(b.keys()-a.keys()),'unchanged':len(a)-len(changed),'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'fail_closed':rejected,'execution':execution,'apple_sdk':'not run: no build authorization','physical_iphone':'pending'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();result=validate(args.before,args.after,args.swiftc);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
