#!/usr/bin/env python3
"""Execute persisted defaults and native silent metadata paths without Apple SDK."""
import argparse
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from validate_quick_format import block, manifest

ROOT=Path(__file__).resolve().parents[1]
E='submodules/TelegramCore/Sources/PendingMessages/EnqueueMessage.swift'
T='submodules/TelegramCore/Sources/PendingMessages/StandaloneSendMessage.swift'
U='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
H='submodules/TelegramCore/Sources/NagramiXSilentSend.swift'
D='submodules/NagramiXMediaSettings/Sources/NagramiXSendSettings.swift'
A='submodules/TelegramCore/Sources/SyncCore/SyncCore_NotificationInfoMessageAttribute.swift'


def production(after):
    enqueue=(after/E).read_text();standalone=(after/T).read_text();ui=(after/U).read_text()
    enum=enqueue.split('public enum EnqueueMessage {',1)[1].split('    public func withUpdatedReplyToMessageId(',1)[0]
    attributes=block(enqueue,'public func withUpdatedAttributes(')
    getter=block(enqueue,'public var attributes:')
    grouping=block(enqueue,'public enum EnqueueMessageGrouping ')
    native=(after/A).read_text().replace('import Postbox','')
    helper=(after/H).read_text().replace('import Postbox','').replace('import NagramiXMediaSettings','')
    batch=enqueue.split('func enqueueMessages(transaction:',1)[1].split('    /**',1)[0].split('{',1)[1]
    share=block(standalone,'if message.isSilent || sendSilently ')
    rpc=block(standalone.split('private func sendMessageContent(',1)[1],'if let attribute = attribute as? NotificationInfoMessageAttribute ')
    setter=block(ui,'updateSendSilently: { value in').split(': ',1)[1].rstrip(',')
    direct=standalone.split('public func standaloneSendMessage(',1)[1].split('\n',2)[1]
    output=grouping+'\nenum EnqueueMessage {\n'+enum+attributes+'\n'+getter+'\n}\n'+native+'\n'+(after/D).read_text()+'\n'+helper+'''
func productionBatch(_ messages: [(Bool,EnqueueMessage)]) -> [(Bool,EnqueueMessage)] {
''' + batch + '''
    return messages
}
func productionShare(_ messages: [ShareMessage]) -> [[MessageAttribute]] {
    let sendSilently = NagramiXSendSettings.sendSilently
    return messages.map { message in
        var attributes: [MessageAttribute] = []
''' + share + '''
        return attributes
    }
}
func productionDirect(_ attributes: [MessageAttribute]) -> [MessageAttribute] {
''' + direct + '''
    return attributes
}
func productionRPCFlags(_ attributes: [MessageAttribute]) -> Int32 {
    var flags: Int32 = 0
    for attribute in attributes {
''' + rpc + '''
    }
    return flags
}
func productionSettingsToggle(_ value: Bool, settingsPromise: SettingsPromise) {
    let callback: (Bool)->Void = ''' + setter + '''
    callback(value)
}
'''
    return output.replace('public ','')


def validate(args):
    plan=json.loads((ROOT/'ios/silent_send_patches.json').read_text())
    a,b=manifest(args.before),manifest(args.after)
    changed={n for n in a if a[n]!=b.get(n)}
    assert changed=={p[0] for p in plan['patches']},changed
    assert b.keys()-a.keys()==set(plan['copies'].values()) and not a.keys()-b.keys()
    assert all(a[n]==digest for n,digest in plan['hashes'].items())
    ui=(args.after/U).read_text()
    assert ui.count('.sendSilently(NagramiXSendSettings.sendSilently)')==1
    assert 'case .sendSilently: return 158' in ui and 'case .sendSilently: return 351' in ui
    assert ui.count('case .sendSilently, .quickFormatting,')==2
    assert 'updated: arguments.updateSendSilently' in ui and 'return strings.nagramiXSendSilentlySearchTerms' in ui
    for lang,title in [('ru','Отправлять без звука'),('en','Send Silently')]:
        text=(args.after/f'submodules/NagramiXCore/Resources/{lang}.lproj/Localizable.strings').read_text()
        assert text.count('"NagramiX.Messages.SendSilently.Title" = "'+title+'";')==1
        assert text.count('"NagramiX.Messages.SendSilently.SearchTerms" = ') == 1
    spec=importlib.util.spec_from_file_location('silent_send',ROOT/'ios/silent_send.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    failures,runs=[],[]
    with tempfile.TemporaryDirectory(prefix='nagramix-silent-') as temp:
        temp=Path(temp)
        def seed(target):
            for n in set(plan['hashes'])|set(plan['provided'].values()):
                (target/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,target/n)
            for n in plan['copies'].values():(target/n).parent.mkdir(parents=True,exist_ok=True)
        def reject(target,label,overlay=ROOT/'ios'):
            old=manifest(target)
            try:mod.apply_silent_send(target,overlay)
            except SystemExit:pass
            else:raise AssertionError(label)
            assert manifest(target)==old,'partial write: '+label
            failures.append(label)
        target=temp/'good';seed(target);mod.apply_silent_send(target,ROOT/'ios')
        assert all((target/n).read_bytes()==(args.after/n).read_bytes() for n in changed|set(plan['copies'].values()))
        reject(target,'reapply')
        for n in set(plan['hashes'])|set(plan['provided'].values()):
            for kind in ['missing','drift']:
                target=temp/(kind+str(len(failures)));seed(target)
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text((target/n).read_text()+'\n// drift')
                reject(target,kind+' '+n)
        for n in plan['copies'].values():
            target=temp/('copy'+str(len(failures)));seed(target);(target/n).write_text('// conflict');reject(target,'copy conflict '+n)
        for index in range(len(plan['patches'])):
            custom=json.loads(json.dumps(plan));custom['patches'][index][1]+=' bad anchor'
            overlay=temp/('overlay'+str(index));overlay.mkdir()
            for name in list(plan['provided'])+list(plan['copies']):
                (overlay/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/name,overlay/name)
            (overlay/'silent_send_patches.json').write_text(json.dumps(custom))
            target=temp/('anchor'+str(index));seed(target);reject(target,'anchor '+str(index),overlay)
        for index,name in enumerate(list(plan['provided'])+list(plan['copies'])):
            for kind in ['missing','empty']:
                overlay=temp/('helper'+str(index)+kind);overlay.mkdir()
                for n in list(plan['provided'])+list(plan['copies']):
                    (overlay/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'ios'/n,overlay/n)
                if kind=='missing':(overlay/name).unlink()
                else:(overlay/name).write_text(' ')
                (overlay/'silent_send_patches.json').write_text(json.dumps(plan))
                target=temp/('helperSource'+str(index)+kind);seed(target);reject(target,kind+' helper '+name,overlay)
        for index,n in enumerate(plan['source_globs']):
            custom=json.loads(json.dumps(plan));target=temp/('glob'+str(index));seed(target)
            (target/n).write_text((target/n).read_text().replace('Sources/**/*.swift','Sources/stale.swift'))
            custom['hashes'][n]=manifest(target)[n]
            overlay=temp/('globOverlay'+str(index));shutil.copytree(ROOT/'ios',overlay)
            (overlay/'silent_send_patches.json').write_text(json.dumps(custom));reject(target,'source glob '+n,overlay)
        code=(ROOT/'scripts/tests/NagramiXSilentSendBoundary.swift').read_text()+'\n'+production(args.after)+'\n'+(ROOT/'scripts/tests/NagramiXSilentSendTests.swift').read_text()
        source=temp/'Tests.swift';source.write_text(code)
        for mode in ['debug','optimized']:
            binary=temp/mode
            command=[str(args.swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(temp/'cache'),str(source),'-o',str(binary)]
            if mode=='optimized':command.insert(1,'-O')
            subprocess.run(command,check=True)
            prefs=temp/('prefs-'+mode);prefs.mkdir()
            env=dict(os.environ,XDG_CONFIG_HOME=str(prefs))
            runs.append(mode+': '+subprocess.check_output([str(binary)],env=env,text=True,timeout=30).strip())
            for action,value in [('fresh','true'),('set','false'),('read','false'),('set','true'),('read','true'),('read','true')]:
                subprocess.run([str(binary),action,value],env=env,check=True,stdout=subprocess.PIPE,timeout=15)
            runs.append(mode+': PASS 6 cold processes')
        swiftFiles={n for n in changed|set(plan['copies'].values())|set(plan['provided'].values()) if n.endswith('.swift')}
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in sorted(swiftFiles)]],check=True)
    for n in ['ios/silent_send.py','ios/apply_features.py','scripts/validate_silent_send.py']:ast.parse((ROOT/n).read_text())
    return dict(outputs=len(b),changed=sorted(changed),added=sorted(b.keys()-a.keys()),unchanged=len(a)-len(changed),guards=len(plan['hashes']),operations=len(plan['patches']),fail_closed=failures,runs=runs,SDK='not run',native_UI_and_network='boundaries, not physical delivery',device='pending')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','swiftc','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
