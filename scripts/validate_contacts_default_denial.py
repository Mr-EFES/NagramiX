#!/usr/bin/env python3
"""Verify silent native contact denial with real pinned SwiftSignalKit."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from validate_contact_chat_readiness import KIT, NATIVE, PIN

ROOT = Path(__file__).resolve().parents[1]
APP = 'submodules/TelegramUI/Sources/ApplicationContext.swift'
MANAGER = 'submodules/TelegramUI/Sources/DeviceContactDataManager.swift'
ACCESS = 'submodules/DeviceAccess/Sources/DeviceAccess.swift'


def between(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


def function(text, marker):
    start = text.index(marker)
    brace = text.index('{', start)
    depth = 1; end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def production(before, after):
    app, manager, access = [(after / n).read_text() for n in [APP, MANAGER, ACCESS]]
    old_app, old_manager = [(before / n).read_text() for n in [APP, MANAGER]]
    def callback(text):
        return between(text, ').startStrict(next: { [weak self] authorizationStatus in\n', '\n        })')
    props = between(manager, '    private var accessInitialized = false', '\n    init(queue: Queue, accountManager:')
    props = props.replace('private ', '').replace('DeviceContactDataContext?', 'DeviceContactDataModernContext?').replace('PresentationPersonNameOrder', 'Int').replace('ExtendedContactDataContext', 'Int')
    methods = '\n'.join(function(manager, marker).replace('private ', '') for marker in [
        '    private func updateAll(', '    private func updateAppSpecificReferences(',
        '    func importable(updated:', '    func appSpecificReferences(updated:'])
    model = '''final class Manager {
    let queue = Queue()
    let accountManager = 0
    var accessInitialized = false
''' + props + '\n' + methods + '''
    func receive(_ authorizationStatus: AccessType) {
        let handler: (AccessType) -> Void = { [weak self] authorizationStatus in
''' + callback(manager) + '''
        }
        handler(authorizationStatus)
    }
    func receivePrevious(_ authorizationStatus: AccessType) {
        let handler: (AccessType) -> Void = { [weak self] authorizationStatus in
''' + callback(old_manager) + '''
        }
        handler(authorizationStatus)
    }
    func signal() -> ContactSignal { Signal { out in self.importable(updated: out.putNext) } }
}
'''
    contacts = between(access, '    static var contacts: Signal<Bool?, NoError> {', '\n    private static let notificationsPromise')
    status = between(access.split('case .contacts:', 1)[1], '\n', '            case .cellularData:')
    authorize = between(access.split('    public static func authorizeAccess(', 1)[1], '                case .contacts:\n', '                case .notifications:')
    os_access = '''final class DeviceAccess {
    private static var contactsPromise = Promise<Bool?>(nil)
    static var contacts: Signal<Bool?, NoError> {''' + contacts + '''
    static func cached() -> Signal<Bool?,NoError> { self.contactsPromise.get() }
    static func reset() { self.contactsPromise = Promise<Bool?>(nil) }
    static func status() -> Signal<AccessType,NoError> {
''' + status + '''
    }
    static func request(_ completion: @escaping (Bool) -> Void) {
''' + authorize + '''
    }
}
'''
    bind_start = '        self.context.account.importableContacts.set(optionalImportableContacts)'
    def binding(text): return bind_start + between(text, bind_start, '\n        let previousTheme =')
    producer = between(app, '        let optionalImportableContacts = ', '\n        self.context.account.importableContacts.set(')
    select = producer.split('        |> mapToSignal', 1)[1]
    pipeline = '''extension TestBinding {
    func bindCurrent(_ optionalImportableContacts: ContactSignal) {
''' + binding(app) + '''
    }
    func bindPrevious(_ optionalImportableContacts: ContactSignal) {
''' + binding(old_app) + '''
    }
}
func productionImportable(settings: Signal<TestPreferences?,NoError>, book: ContactSignal) -> ContactSignal {
    let importableContacts = book
    return settings |> mapToSignal''' + select + '''
}
func observeHistory(_ context: TestContext, history: Signal<Bool,NoError> = .single(true), next: @escaping (Set<String>) -> Void) -> Disposable {
    let numbers = context.sharedContext.deviceContactPhoneNumbers.get() |> distinctUntilChanged
    return combineLatest(''' + ',\n'.join(['history'] + ['Signal<Bool,NoError>.single(true)'] * 23 + ['numbers', 'Signal<Bool,NoError>.single(true)']) + ''').start(next: { next($0.24) })
}
'''
    notice = '                let savedContactsTimestamp = ' + between(app, '                let savedContactsTimestamp = ', '                let notificationsTimestamp = ')
    order = '                let config = splitTest.configuration' + between(app, '                let config = splitTest.configuration', '                if let (state, modal) = requestedPermissions.first {')
    permissions = '''func productionRequests(_ config: Config, saved: Int32?) -> ([PermissionKind], [Int32]) {
    let context = NoticeContext()
    let contactsPermissionWarningNotice = NoticeValue(value:saved)
''' + notice + '''
    let splitTest = SplitTest(configuration:config)
    let position = 0
    let notificationsTimestamp: Int32? = nil
    let cellularDataTimestamp: Int32? = nil
    let required: (PermissionState,PermissionState,PermissionState,PermissionState) = (.contacts(.requestable),.notifications(.requestable),.cellularData(.denied),.siri(.requestable))
''' + order + '''
    let result: [PermissionKind] = requestedPermissions.map { state, _ in
        switch state { case .contacts: return .contacts; case .notifications: return .notifications; case .cellularData: return .cellularData; case .siri: return .siri }
    }
    return (result,context.sharedContext.accountManager.writes)
}
'''
    return 'import Foundation\n' + model + os_access + pipeline + permissions


def validate(args):
    plan = json.loads((ROOT / 'ios/contacts_default_denial_patches.json').read_text())
    before, after = manifest(args.before), manifest(args.after)
    assert before.keys() == after.keys()
    changed = {n for n in before if before[n] != after[n]}
    assert changed == set(plan['hashes']) == {APP, MANAGER}
    texts = {n:(args.before/n).read_text() for n in plan['hashes']}
    assert all(before[n] == sha for n,sha in plan['hashes'].items())
    for n,old,new,count in plan['patches']:
        assert texts[n].count(old) == count
        texts[n] = texts[n].replace(old,new,count)
    assert all(text == (args.after/n).read_text() for n,text in texts.items())
    tree = json.loads(args.upstream_tree.read_text()); assert tree['sha'] == PIN
    entries = {e['path']:e for e in tree['tree'] if e['type']=='blob'}
    for n in [MANAGER]:
        data=(args.before/n).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==entries[n]['sha']
    raw_access = args.raw / ACCESS
    data=raw_access.read_bytes(); assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==entries[ACCESS]['sha']
    a,b=(args.before/APP).read_text(),(args.after/APP).read_text()
    assert 'var order = config.order\n' in b and 'config.order.filter { $0 != .contacts }' not in b
    assert '.single(Set<String>()) |> then(deviceContactPhoneNumbers)' not in b
    marker='        let importableContacts = '
    assert between(a,marker,'        self.context.account.importableContacts.set(')==between(b,marker,'        self.context.account.importableContacts.set(')
    assert 'return ContactsSettings(synchronizeContacts: true)' in (args.upstream/'submodules/TelegramCore/Sources/SyncCore/SyncCore_ContactsSettings.swift').read_text()
    # No poisoned authorization cache, OS result or contact CRUD patch.
    assert (args.before/ACCESS).read_bytes()==(args.after/ACCESS).read_bytes()
    assert 'self.contactsPromise.set(.single(false))' not in '\n'.join(p[2] for p in plan['patches'])
    spec=importlib.util.spec_from_file_location('contacts_default_denial',ROOT/'ios/contacts_default_denial.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rejected=[];execution=[]
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp)
        def seed(target):
            for n in plan['hashes']:
                p=target/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.before/n,p)
        def reject(target,label,overlay=ROOT/'ios'):
            saved=manifest(target)
            try:module.apply_contacts_default_denial(target,overlay)
            except (SystemExit,FileNotFoundError):pass
            else:raise AssertionError(label)
            assert manifest(target)==saved
            rejected.append(label)
        target=temp/'valid';seed(target);module.apply_contacts_default_denial(target,ROOT/'ios')
        assert all((target/n).read_text()==text for n,text in texts.items());reject(target,'reapply')
        for i,n in enumerate(plan['hashes']):
            for kind in ['missing','drift']:
                target=temp/(kind+str(i));seed(target)
                if kind=='missing':(target/n).unlink()
                else:(target/n).write_text((target/n).read_text()+'\n// drift\n')
                reject(target,kind+' '+n)
        overlay=temp/'broken';overlay.mkdir();invalid=json.loads(json.dumps(plan));invalid['patches'][-1][1]+='// bad last anchor'
        (overlay/'contacts_default_denial_patches.json').write_text(json.dumps(invalid));target=temp/'anchor';seed(target);reject(target,'last anchor',overlay)
        sources=[]
        for n in NATIVE:
            data=(args.upstream/(KIT+n)).read_bytes()
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==entries[KIT+n]['sha']
            text=data.decode();text=('import CoreFoundation\n'+text) if n=='Signal_Meta.swift' else text
            p=temp/n;p.write_text(text);sources.append(p)
        p=temp/'Production.swift';p.write_text(production(args.before,args.after));sources.append(p)
        sources += [ROOT/'scripts/tests/NagramiXContactsDefaultDenialBoundary.swift',ROOT/'scripts/tests/NagramiXContactsDefaultDenialTests.swift']
        for mode in ['debug','optimized']:
            binary=temp/('tests-'+mode)
            cmd=[str(args.swiftc),'-warnings-as-errors','-module-cache-path',str(temp/'cache'),*map(str,sources),'-o',str(binary)]
            if mode=='optimized':cmd.insert(1,'-O')
            subprocess.run(cmd,check=True)
            execution.append(mode+': '+subprocess.check_output([str(binary)],text=True,timeout=30).strip())
        subprocess.run([str(args.swiftc),'-frontend','-parse',*[str(args.after/n) for n in sorted(changed)]],check=True)
    for n in ['ios/apply_features.py','ios/contacts_default_denial.py','scripts/validate_contacts_default_denial.py']:ast.parse((ROOT/n).read_text())
    return {'native_outputs':len(after),'changed':sorted(changed),'unchanged':len(after)-len(changed),
            'sha_guards':len(plan['hashes']),'exact_operations':len(plan['patches']),'fail_closed':rejected,
            'signal_implementation':'11 real pinned SwiftSignalKit files; native 26-way history combine',
            'execution':execution,'native_sdk':'not run: separate build command required','physical_iPhone':'pending'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['before','after','upstream','upstream-tree','raw','swiftc','report']:parser.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args();result=validate(args)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
