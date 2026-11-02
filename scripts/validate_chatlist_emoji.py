#!/usr/bin/env python3
"""Validate native chat-list emoji hydration and prefix offsets without an IPA."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from validate_quick_format import manifest

ROOT=Path(__file__).resolve().parents[1]
NODE='submodules/ChatListUI/Sources/Node/ChatListItem.swift'
STRINGS='submodules/ChatListUI/Sources/Node/ChatListItemStrings.swift'
HELPER='submodules/ChatListUI/Sources/Node/NagramiXChatListPreviewEmoji.swift'
PIN='submodules/TelegramStringFormatting/Sources/NagramiXPinnedPreviewEmoji.swift'


def validate(args):
    plan=json.loads((ROOT/'ios/chatlist_emoji_patches.json').read_text())
    a,b=manifest(args.before),manifest(args.after)
    assert {n for n in a.keys() & b.keys() if a[n]!=b[n]}=={NODE,STRINGS}
    assert b.keys()-a.keys()=={HELPER} and not a.keys()-b.keys()
    assert plan['hashes']=={n:a[n] for n in plan['hashes']}
    assert (args.after/PIN).read_bytes()==(args.before/PIN).read_bytes()
    node=(args.after/NODE).read_text();strings=(args.after/STRINGS).read_text()
    assert strings.count('nagramiXChatListPrependMediaPrefix(')==6
    assert node.count('nagramiXPreviewEmoji.update(')==1 and node.count('nagramiXPreviewEmoji.prepare(')==1
    assert node.index('nagramiXPreviewEmoji.prepare(')<node.index('nagramiXPreviewEmojiSnapshot.applying(')
    assert 'let params = strongSelf.layoutParams' in node and 'apply(false, false)' in node
    spec=importlib.util.spec_from_file_location('emoji',ROOT/'ios/chatlist_emoji.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    entries={e['path']:e for e in json.loads(args.upstream_tree.read_text())['tree'] if e['type']=='blob'}
    for name in ['Atomic.swift','Disposable.swift']:
        data=(args.signal_source/name).read_bytes()
        expected=entries['submodules/SSignalKit/SwiftSignalKit/Source/'+name]['sha']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected
    failures,runs=[],[]
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        def seed(label):
            target=folder/label
            for n in plan['hashes']:
                (target/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,target/n)
            return target
        def reject(target,label,overlay=ROOT/'ios'):
            previous=manifest(target)
            try:module.apply_chatlist_emoji(target,overlay)
            except SystemExit:pass
            else:raise AssertionError(label)
            assert manifest(target)==previous;failures.append(label)
        target=seed('valid');module.apply_chatlist_emoji(target,ROOT/'ios')
        assert all((target/n).read_bytes()==(args.after/n).read_bytes() for n in [NODE,STRINGS,HELPER])
        reject(target,'reapply')
        for index,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                target=seed(kind+str(index))
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text('// drift')
                reject(target,kind+' '+n)
        for index in range(len(plan['patches'])):
            invalid=json.loads(json.dumps(plan));invalid['patches'][index][1]+=' missing'
            overlay=folder/('overlay'+str(index));overlay.mkdir()
            (overlay/'chatlist_emoji_patches.json').write_text(json.dumps(invalid))
            for n in plan['copies']:
                (overlay/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/n,overlay/n)
            reject(seed('anchor'+str(index)),'anchor '+str(index),overlay)
        target=seed('collision');(target/HELPER).write_text('// keep');reject(target,'helper collision')
        overlay=folder/'missing-helper';overlay.mkdir();shutil.copyfile(ROOT/'ios/chatlist_emoji_patches.json',overlay/'chatlist_emoji_patches.json')
        reject(seed('missinghelper'),'missing helper',overlay)
        # Only external module imports are removed. Helpers and state machine are
        # production source; native Atomic/Disposable are compiled byte-for-byte.
        code=(ROOT/'scripts/tests/NagramiXChatListEmojiBoundary.swift').read_text()
        for path in [args.after/PIN,args.after/HELPER]:
            source=path.read_text()
            for name in ['Postbox','TelegramCore','TelegramStringFormatting','SwiftSignalKit','TextFormat']:source=source.replace('import '+name+'\n','')
            code+='\n'+source
        code+='\n'+(ROOT/'scripts/tests/NagramiXChatListEmojiTests.swift').read_text()
        tests=folder/'Tests.swift';tests.write_text(code)
        for mode in ['debug','optimized']:
            binary=folder/mode
            cmd=[str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(folder/'cache'),str(args.signal_source/'Atomic.swift'),str(args.signal_source/'Disposable.swift'),str(tests),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            runs.append(mode+': '+subprocess.check_output([str(binary)],text=True,timeout=30).strip())
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in [NODE,STRINGS,HELPER]]],check=True)
    for n in ['ios/chatlist_emoji.py','ios/apply_features.py','scripts/validate_chatlist_emoji.py']:ast.parse((ROOT/n).read_text())
    return dict(outputs=len(b),changed=[NODE,STRINGS],added=[HELPER],unchanged=len(a)-2,guards=len(plan['hashes']),operations=len(plan['patches']),fail_closed=failures,runtime=runs,native_synchronization='verified pinned Atomic.swift and Disposable.swift',AttributedRuns_UIKit_Engine_TextNodeWithEntities='boundaries; native NSString UTF-16 lengths executed; physical device pending',SDK_IPA='not started')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','signal-source','upstream-tree','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
