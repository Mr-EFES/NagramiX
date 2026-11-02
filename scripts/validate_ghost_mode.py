#!/usr/bin/env python3
"""Verify pinned ghost integration and execute the actual settings/presence policy."""
import argparse, hashlib, importlib.util, json, shutil, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def manifest(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def validate(before, after, swiftc):
    plan = json.loads((ROOT/'ios/ghost_mode_patches.json').read_text())
    a,b = manifest(before),manifest(after)
    model = 'submodules/NagramiXMediaSettings/Sources/NagramiXGhostSettings.swift'
    read_mode = 'submodules/NagramiXMediaSettings/Sources/NagramiXReadModeSettings.swift'
    privacy = 'submodules/NagramiXMediaSettings/Sources/NagramiXPrivacySettings.swift'
    assert b.keys()-a.keys() == {model,read_mode,privacy,*plan['copies'].values()}
    assert not a.keys()-b.keys()
    assert (after/model).read_bytes() == (ROOT/'ios/Sources/NagramiXMediaSettings/Sources/NagramiXGhostSettings.swift').read_bytes()
    extras = {'submodules/NagramiXMediaSettings/Sources/NagramiXStorySettings.swift','submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift',*[f'submodules/NagramiXCore/Resources/{l}.lproj/Localizable.strings' for l in ['ru','en']]}
    changed = {n for n in a if a[n]!=b[n]}
    assert changed == {p[0] for p in plan['patches']}|extras, changed
    restored = {n:(after/n).read_text() for n in plan['hashes']}
    for n,old,new,count in reversed(plan['patches']):
        assert restored[n].count(new)==count,(n,new[:80])
        restored[n]=restored[n].replace(new,old,count)
    assert all(restored[n].encode()==(before/n).read_bytes() for n in restored)
    assert all(hashlib.sha256((before/n).read_bytes()).hexdigest()==sha for n,sha in plan['hashes'].items())
    spec=importlib.util.spec_from_file_location('ghost_overlay',ROOT/'ios/ghost_mode.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[]
    with tempfile.TemporaryDirectory() as folder:
        native=Path(folder)/'native'
        def seed():
            if native.exists():shutil.rmtree(native)
            for n in plan['hashes']:
                p=native/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(before/n,p)
        def reject(label):
            old=manifest(native)
            try:module.apply_ghost_mode(native,ROOT/'ios')
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(native)==old,label
            rejected.append(label)
        seed();module.apply_ghost_mode(native,ROOT/'ios')
        assert all((native/n).read_bytes()==(after/n).read_bytes() for n in [*plan['hashes'],*plan['copies'].values()])
        reject('reapply')
        for n in plan['hashes']:
            seed();p=native/n;p.write_bytes(p.read_bytes()+b'\n// drift');reject('drift '+n)
            seed();(native/n).unlink();reject('missing '+n)
        for n in plan['copies'].values():
            seed();p=native/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('collision');reject('collision '+n)
    executed=[]
    with tempfile.TemporaryDirectory() as folder:
        for mode in ['debug','optimized']:
            args=[str(swiftc),'-warnings-as-errors','-module-cache-path',folder+'/cache',str(after/read_mode),str(after/privacy),str(after/model),str(ROOT/'scripts/tests/NagramiXGhostSettingsTests.swift'),'-o',folder+'/test']
            if mode=='optimized':args.insert(1,'-O')
            subprocess.run(args,check=True);executed.append(mode+': '+subprocess.check_output([folder+'/test'],text=True).strip())
        files=[after/n for n in sorted(changed|set(plan['copies'].values())) if n.endswith('.swift')]
        subprocess.run([str(swiftc),'-frontend','-parse',*map(str,files)],check=True)
    # No global privacy-disable window, fake API results, new read-state tables,
    # request monkey-patching, or edits to encryption/authorization are introduced.
    actions=(after/'submodules/TelegramCore/Sources/NagramiXGhostReadActions.swift').read_text()
    assert 'NagramiXGhostSettings.update' not in actions and 'upTo messageId' in actions
    assert 'upTo messageId: MessageId' in actions and 'let message = transaction.getMessage(messageId)' in actions
    assert 'nagramiXSendReadAcknowledgement(account: account, index: index, threadId: threadId, source: .action)' in actions
    assert 'key.setInt64(8, value: peerId.toInt64())' in actions
    assert 'transaction.setPreferencesEntry(key: key, value: PreferencesEntry(NagramiXGhostReadMarker' in actions
    read_state=(after/'submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift').read_text()
    assert read_state.index('nagramiXPreservePrivateRead(transaction:') < read_state.index('if updatedCount != 0 || updatedMarkedUnread')
    assert 'Namespace' not in ''.join(p[0] for p in plan['patches'] if '/Postbox/' in p[0])
    story=(after/'submodules/NagramiXMediaSettings/Sources/NagramiXStorySettings.swift').read_text()
    assert story.count('NagramiXPrivacySettings.update { $0[.storyReads] = anonymousViewing }')==1
    assert 'UserDefaults.standard.set' not in story and '||' not in story
    return {'outputs':len(b),'changed':sorted(changed),'new':sorted(b.keys()-a.keys()),'unchanged':len(a)-len(changed),'sha_guards':len(plan['hashes']),'reverse_patches':len(plan['patches']),'guard_cases':rejected,'execution':executed,'apple_sdk':'pending','device':'pending'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    report=validate(a.before,a.after,a.swiftc);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
