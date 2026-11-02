#!/usr/bin/env python3
"""Validate source-poster leases and PiP presentation ordering without an IPA."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GALLERY = 'submodules/GalleryUI/Sources/GalleryController.swift'
NODE = 'submodules/GalleryUI/Sources/GalleryControllerNode.swift'
ITEM = 'submodules/GalleryUI/Sources/Items/UniversalVideoGalleryItem.swift'
GESTURE = 'submodules/GalleryUI/Sources/NagramiXPiPGestureController.swift'
VISUAL = 'submodules/GalleryUI/Sources/NagramiXPiPVisualHandoff.swift'
KIT = 'submodules/SSignalKit/SwiftSignalKit/Source/'
NATIVE = ['Atomic.swift','Bag.swift','Disposable.swift','Subscriber.swift','Signal.swift','Promise.swift',
          'Signal_Mapping.swift','Signal_Meta.swift','Signal_Take.swift','Signal_Combine.swift','Signal_Single.swift']


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def validate(args):
    plan = json.loads((ROOT / 'ios/pip_visual_patches.json').read_text())
    a, b = manifest(args.before), manifest(args.after)
    changed = {n for n in a.keys() & b.keys() if a[n] != b[n]}
    assert changed == {GALLERY, NODE, ITEM, GESTURE}, changed
    assert b.keys() - a.keys() == {VISUAL} and not a.keys() - b.keys()
    assert plan['hashes'] == {n: a[n] for n in plan['hashes']}
    templates = {m: (ROOT / 'ios' / n).read_text().rstrip('\n') for m,n in plan['templates'].items()}
    text = {n: (args.before / n).read_text() for n in plan['hashes']}
    for n, old, new, count in plan['patches']:
        for marker, value in templates.items(): new = new.replace(marker,value)
        assert text[n].count(old) == count
        text[n] = text[n].replace(old,new,count)
    assert all(text[n] == (args.after / n).read_text() for n in text)
    assert (args.after / GESTURE).read_bytes() == (ROOT / 'ios/Sources/GalleryUI/NagramiXPiPGestureController.swift').read_bytes()
    assert (args.after / VISUAL).read_bytes() == (ROOT / 'ios/Sources/GalleryUI/NagramiXPiPVisualHandoff.swift').read_bytes()
    spec = importlib.util.spec_from_file_location('pip_visual',ROOT / 'ios/pip_visual.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rejected=[]
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        def seed(target):
            for n in plan['hashes']:
                p=target/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,p)
        def reject(target,label,overlay=ROOT/'ios'):
            saved=manifest(target)
            try:module.apply_pip_visual(target,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(target)==saved,label
            rejected.append(label)
        target=folder/'valid';seed(target);module.apply_pip_visual(target,ROOT/'ios')
        assert all((target/n).read_text()==text[n] for n in text)
        reject(target,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                target=folder/(kind+str(i));seed(target)
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text((target/n).read_text()+'\n// drift\n')
                reject(target,kind+' '+n)
        resources=[*plan['templates'].values(),*plan['copies']]
        for i,missing in enumerate(resources):
            overlay=folder/('overlay'+str(i));overlay.mkdir()
            shutil.copyfile(ROOT/'ios/pip_visual_patches.json',overlay/'pip_visual_patches.json')
            for name in resources:
                if name==missing:continue
                p=overlay/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/name,p)
            target=folder/('resource'+str(i));seed(target);reject(target,'missing resource '+missing,overlay)
        target=folder/'collision';seed(target);p=target/VISUAL;p.write_text('// collision');reject(target,'helper collision')
        overlay=folder/'anchor-overlay';overlay.mkdir();invalid=json.loads(json.dumps(plan));invalid['patches'][-1][1]+='// missing'
        (overlay/'pip_visual_patches.json').write_text(json.dumps(invalid))
        for name in resources:
            p=overlay/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/name,p)
        target=folder/'anchor';seed(target);reject(target,'last anchor mismatch',overlay)

    gallery=(args.after/GALLERY).read_text();item=(args.after/ITEM).read_text();node=(args.after/NODE).read_text()
    old_item=(args.before/ITEM).read_text()
    assert 'func pictureInPictureControllerWillStartPictureInPicture(' not in old_item
    assert 'self.beginCustomDismiss(.pip)\n                controller.view.alpha = 0.0' in old_item
    assert 'pictureInPictureControllerWillStartPictureInPicture' in item
    assert 'self.lifecycle.phase == .starting' in item
    assert 'if !self.lifecycle.transferred { self.rollbackTransition() }' in item
    assert 'transition: { visual.willStart() }, rollbackTransition: { visual.cancel() }' in item
    assert 'self.beginCustomDismiss(.pip)\n                visual.commit()' in item
    assert 'visual.restore()' in item
    assert item.count('startPictureInPicture()') == 1
    assert 'controller.view.layer.presentation()?.opacity' in item
    assert 'sourcePreview: { [weak self] visible in' in node
    assert gallery.count('addSource(combineLatest(self._hiddenMedia.get(), self.nagramiXPiPSourcePreview.get())')==2
    assert 'updateCanReadHistory' not in plan['patches'][0][2]+plan['patches'][1][2]
    # Audio, decoder ownership, geometry and all unrelated feature outputs are
    # byte-identical to the prior verified overlay; no window-position API added.
    for n in ['submodules/GalleryUI/Sources/NagramiXPiPLifecycle.swift',
              'submodules/GalleryUI/Sources/NagramiXPiPSourceGeometry.swift',
              'submodules/TelegramUI/Sources/MediaManager.swift',
              'submodules/AccountContext/Sources/UniversalVideoNode.swift']:
        assert a[n]==b[n]
    tree=json.loads(args.upstream_tree.read_text());assert tree['sha']=='f1dd7a2dbd02cbbf513e75d5695d8d36d1cf5838'
    entries={e['path']:e for e in tree['tree'] if e['type']=='blob'}
    for name in NATIVE:
        data=(args.signal_source/(KIT+name)).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==entries[KIT+name]['sha']
    # Extract the exact GalleryController setter and mapper. Actual reactive
    # operators are upstream; account/message/media and UIKit are boundaries.
    fields=gallery.split('    private let _hiddenMedia = ',1)[1].split('    private let replaceRootController:',1)[0]
    mapper=gallery.split('|> map { messageIdAndMedia, previewVisible in',1)[1].split('\n        })',1)[0]
    harness='''import Foundation
typealias MessageId=Int
struct TestMedia: Equatable { let id: Int }
typealias Media=TestMedia
enum GalleryHiddenMediaId: Equatable { case chat(Int,Int,TestMedia) }
struct TestAccount { let id=5 }
struct TestContext { let account=TestAccount() }
final class GalleryPreviewHarness {
'''+ '    private let _hiddenMedia = '+fields+'''
    var hiddenMedia: Promise<(MessageId,Media)?> { self._hiddenMedia }
    func source() -> Signal<GalleryHiddenMediaId?,NoError> {
        let context=TestContext()
        return combineLatest(self._hiddenMedia.get(),self.nagramiXPiPSourcePreview.get())
        |> map { messageIdAndMedia, previewVisible in
'''+mapper+'''\n        }
    }
}
'''
    # fields includes only the new property/method block and original whitespace.
    assert 'replaceRootController' not in harness
    results=[]
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp);sources=[]
        for name in NATIVE:
            text=(args.signal_source/(KIT+name)).read_text()
            if name=='Signal_Meta.swift':text='import CoreFoundation\n'+text
            p=folder/name;p.write_text(text);sources.append(p)
        p=folder/'QueueBoundary.swift';p.write_text('public final class Queue {}\npublic func deliverOn<T,E>(_ q: Queue)->(Signal<T,E>)->Signal<T,E> { { _ in fatalError("unexpected scheduling") } }\n');sources.append(p)
        p=folder/'GalleryPreview.swift';p.write_text(harness);sources.append(p)
        sources += [args.after/VISUAL,ROOT/'scripts/tests/NagramiXPiPVisualHandoffTests.swift']
        for mode in ['debug','optimized']:
            binary=folder/('visual-'+mode)
            cmd=[str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(folder/'cache'),*map(str,sources),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            results.append(mode+': '+subprocess.check_output([str(binary)],text=True,timeout=30).strip())
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in sorted(changed|{VISUAL})]],check=True)
    for n in ['ios/pip_visual.py','ios/apply_features.py']:ast.parse((ROOT/n).read_text())
    return {'outputs':len(b),'changed':sorted(changed),'added':[VISUAL],'unchanged':len(a)-len(changed),
            'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'fail_closed':rejected,
            'runtime':results,'signal_implementation':'11 actual pinned SwiftSignalKit files',
            'UIKit_AVKit_rendering':'requires Apple SDK and physical iPhone','IPA':'not started'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['before','after','swiftc','signal-source','upstream-tree','report']:
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
