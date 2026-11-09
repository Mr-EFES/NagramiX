#!/usr/bin/env python3
"""Проверить порядок DNS/DoH/IPv6, удаление и сохранение пользовательского DNS."""
import argparse
import json
import os
from pathlib import Path
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import run, execute
import proxy_doh_editor_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STAGE='proxy_doh_editor'


def contract(source):
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='round_video_editor'
    assert set(plan['outputs'])=={runtime.TAB,runtime.UI,runtime.EDITOR}
    assert len(plan['guards'])==17 and not plan['copies'] and not plan['deletions'] and not plan['native_inputs']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():
        assert digest(source/name)==sha,name
    previous=lambda name:(ROOT/'ios'/plan['previous'][name]).read_text()
    tab=(source/runtime.TAB).read_text()
    assert block(tab,'public enum NagramiXDnsProvider:')==block(previous(runtime.TAB),'public enum NagramiXDnsProvider:')
    history=block(tab,'public enum NagramiXDnsProviderHistory {')
    # Pin the entire aggregate model and its unrelated persistence/notifications.
    without_history=tab.replace('// Remember only a real non-custom choice; custom URL edits must not replace it.\n'+history+'\n\n','')
    hook='        NagramiXDnsProviderHistory.remember(previous: previousDnsProvider, current: value.dnsProvider, in: defaults)\n'
    assert without_history.replace(hook,'')==previous(runtime.TAB)
    assert tab.index(hook)<tab.index('        defaults.set(value.dnsProvider.rawValue, forKey: Key.dnsProvider)')
    ui=(source/runtime.UI).read_text()
    assert block(ui,'    var stableId: ProxySettingsControllerEntryId {')==block(previous(runtime.UI),'    var stableId: ProxySettingsControllerEntryId {')
    assert 'case .dns: return 1\n        case .customDoh: return 2\n        case .preferIPv6: return 3' in ui
    assert ui.index('    entries.append(.dns(')<ui.index('    if nagramiXSettings.dnsProvider == .customDoh {')<ui.index('    entries.append(.preferIPv6(')<ui.index('    entries.append(.autoSwitch(')
    assert 'let previous = NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current: $0.dnsProvider)' in ui
    assert '$0.customDohUrl = ""\n                $0.dnsProvider = previous' in ui
    editor=(source/runtime.EDITOR).read_text()
    old_editor=previous(runtime.EDITOR)
    assert block(editor,'private func validatedNagramiXDohUrl(')==block(old_editor,'private func validatedNagramiXDohUrl(')
    start='    let content: [AnyComponentWithIdentity<AlertComponentEnvironment>] = ['
    assert editor[editor.index(start):editor.index('    let actions:')]==old_editor[old_editor.index(start):old_editor.index('    var actions:')]
    actions=editor[editor.index('    let actions:'):editor.index('    let controller =')]
    assert actions.count('.init(')==2 and 'strings.Common_Delete' in actions and 'strings.nagramiXSave' in actions
    assert 'strings.Common_Cancel' not in editor and 'hasClearButton: true' in editor
    assert 'AlertScreen.Configuration(allowInputInset: true)' in editor
    assert 'controller.dismissed = { _ in\n        _ = submission.finish()\n        validationDisposable.dispose()' in editor
    # Clear-text behavior, two-button sizing, endpoint validation and reconnect
    # remain native exact guards. New UI strings/dependencies are unnecessary.
    for name in [runtime.ALERT,
                 'submodules/TelegramUI/Components/AlertComponent/AlertInputFieldComponent/Sources/AlertInputFieldComponent.swift',
                 'submodules/MtProtoKit/Sources/NagramiXDNSResolver.m',
                 'submodules/TelegramCore/Sources/Network/Network.swift',
                 'submodules/NagramiXMediaSettings/Sources/NagramiXProxyPreferences.swift']:
        assert name in plan['guards']
    return plan


def negatives(fixtures):
    def change(name,suite,old,new,diagnostic):
        text=fixtures[suite];assert old in text,old
        return name,text.replace(old,new,1),diagnostic
    return [
        change('missing-history','history','if previous != .customDoh && current == .customDoh {','if previous == .customDoh && current == .customDoh {','exact prior provider ID including System zero is persisted'),
        change('history-overwritten-by-edit','history','if previous != .customDoh && current == .customDoh {','if current == .customDoh {','editing custom URL preserves previous DNS'),
        change('forced-system-restore','history','return previous','return .system','editing custom URL preserves previous DNS'),
        change('third-action-overflow','controller','        .init(title: strings.Common_Delete,','        .init(title: strings.Common_Delete),\n        .init(title: strings.Common_Delete,','exactly Delete and Save even before first custom save'),
        change('double-delete','controller','        guard submission.finish() else { return }\n        validationDisposable.dispose()','        validationDisposable.dispose()','Delete commits and dismisses once'),
        change('late-save-after-delete','controller','            guard submission.finish() else { return }\n            didResolve = true','            _ = submission.finish()\n            didResolve = true','Delete cancels pending test and rejects late Save success'),
        change('failed-save-locks-retry','controller','self.state = .editing\n        return true','self.state = .validating\n        return true','failure permits an explicit retry'),
    ]


def public_api(swiftc,source,root):
    root.mkdir()
    tab=(source/runtime.TAB).read_text()
    model=root/'Core.swift'
    model.write_text('import Foundation\n'+block(tab,'public enum NagramiXDnsProvider:')+'\n'+block(tab,'public enum NagramiXDnsProviderHistory {'))
    run([swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',root/'cache','-emit-module',
         '-module-name','NagramiXCore',model,'-emit-module-path',root/'NagramiXCore.swiftmodule'])
    caller=root/'SettingsUI.swift'
    clear=block((source/runtime.UI).read_text(),'        }, clear: {')
    clear=clear[clear.index('{')+1:-1]
    caller.write_text('import Foundation\nimport NagramiXCore\nstruct Settings {var dnsProvider=NagramiXDnsProvider.customDoh;var customDohUrl="https://dns.example.org"}\n'
                      'func updateNagramiXSettings(_ f:(inout Settings)->Void){var v=Settings();f(&v)}\n'
                      'func removeEndpoint(){\n'+clear+'\n}\n')
    run([swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',root/'cache','-typecheck','-I',root,caller])
    return 'production public DNS types + actual SettingsUI delete callback typechecked separately'


def cold_processes(swiftc,root,fixture):
    path=root/'cold.swift';path.write_text(fixture);results=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=root/('cold-'+mode)
        run([swiftc,'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',root/'cache',*flags,path,'-o',binary])
        env=dict(os.environ,XDG_CONFIG_HOME=str(root/('cold-prefs-'+mode)))
        for action,value in [('write','0'),('read','0'),('write','1'),('read','1'),('write','5'),('read','5')]:
            result=run([binary,'nagramix.doh.cold',action,value],env=env,timeout=30)
            assert 'PASS DoH cold process' in result.stdout
            results.append({'mode':mode,'action':action,'provider':value,'passed':True})
        binary.unlink()
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();plan=contract(args.source);before=manifest(args.source)
    fixtures={name:make(args.source) for name,make in [('history',runtime.history),('controller',runtime.controller),('geometry',runtime.geometry)]}
    with tempfile.TemporaryDirectory(prefix='nagramix-proxy-doh-') as temporary:
        root=Path(temporary)
        rejected=guard_checks(args.source,STAGE,plan,root/'guards')
        results=[]
        for name,text in fixtures.items():results+=execute(args.swiftc,root,name,text)
        for name,text,diagnostic in negatives(fixtures):results+=execute(args.swiftc,root,name,text,diagnostic)
        cold=cold_processes(args.swiftc,root,fixtures['history'])
        api=public_api(args.swiftc,args.source,root/'api')
        for name in plan['outputs']:run([args.swiftc,'-frontend','-parse',args.source/name])
    assert manifest(args.source)==before
    run(['python3',args.source/'build-system/Make/PostboxImportCheck.py',args.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'fail_closed':len(rejected),
            'executions':results,'cold_processes':cold,'public_api':api,'swift_parse':3,'source_files':len(before),
            'source_unchanged_by_checks':True,'native_postbox_imports':'passed',
            'boundary':'Actual DoH controller, URL validation, submission state, DNS history and native horizontal '
                       'button geometry execute. Alert, input field, transport and Signal are explicit adapters; '
                       'late transport callbacks are intentionally delivered after disposal to exercise terminal guards. '
                       'Production settings persistence and callback API are checked; actual UIKit rendering, live '
                       'DoH and Apple SDK are not proven.',
            'apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('outputs','executions','cold_processes')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
