#!/usr/bin/env python3
"""Проверить скрытие предложений Premium и сохранение остальных уведомлений."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from late_source_stages import LATE_SOURCE_STAGES, verified_prefix
from validate_quick_format import block, manifest
from validate_upstream_13_2_release import checked_plan, digest, guard_checks
from validate_local_copy_delivery import run, execute
import hide_premium_offers_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STAGE='hide_premium_offers'


def contract(source):
    plan=checked_plan(STAGE)
    assert plan['required_previous_stage']=='download_sheet_corners'
    assert len(plan['inputs'])==76 and len(plan['guards'])==19 and len(plan['native_inputs'])==2
    assert not plan['copies'] and not plan['deletions']
    assert verified_prefix(source)==LATE_SOURCE_STAGES.index(STAGE)+1
    for name,sha in {**plan['outputs'],**plan['guards']}.items():assert digest(source/name)==sha,name
    previous=lambda name:(ROOT/'ios'/plan['previous'][name]).read_text()
    for name,sha in plan['native_inputs'].items():
        data=previous(name).encode();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==sha
    tab=(source/runtime.TAB).read_text()
    prefs=block(tab,'public enum NagramiXPremiumOfferSettings {')
    assert tab.replace('// This independent setting cannot be reset by aggregate tab-settings updates.\n'+prefs+'\n\n','')==previous(runtime.TAB)
    assert 'defaults.object(forKey: self.key) as? Bool ?? true' in prefs
    ui=(source/runtime.UI).read_text();old=previous(runtime.UI)
    def ids(text):
        value=block(text,'    var stableId: Int32 {')
        return re.findall(r'case (\.[\w]+): return (-?\d+)',value)
    assert set(ids(old))<set(ids(ui)) and set(ids(ui))-set(ids(old))=={('.hidePremiumOffers','5031')}
    assert sum(v=='5031' for _,v in ids(ui))==1
    assert 'case .hidePremiumOffers: return 77' in ui
    assert 'title: presentationData.strings.nagramiXHidePremiumOffers, text: presentationData.strings.nagramiXHidePremiumOffersInfo' in ui
    assert '.hidePremiumOffers(NagramiXPremiumOfferSettings.isHidden())' in ui
    assert 'NagramiXPremiumOfferSettings.setHidden(value)\n            settingsPromise.set(NagramiXTabSettings.current)' in ui
    assert 'maximumNumberOfLines: 0' in ui[ui.index('case let .hidePremiumOffers(value):'):ui.index('case .hideGreetingStickerInfo:\n')]
    context=(source/runtime.CONTEXT).read_text();old=previous(runtime.CONTEXT)
    marker='public final class GlobalControlPanelsContext {'
    body=context[context.index(marker):]
    body=body.replace('                    accountFreezeConfiguration,\n                    nagramiXPremiumOffersHiddenSignal()\n                )','                    accountFreezeConfiguration\n                )')
    body=body.replace('birthdays, starsSubscriptionsContext, accountFreezeConfiguration, hidePremiumOffers -> Signal<ChatListNotice?, NoError> in\n                    let suggestions = nagramiXChatListSuggestions(suggestions, hidePremiumOffers: hidePremiumOffers)',
                      'birthdays, starsSubscriptionsContext, accountFreezeConfiguration -> Signal<ChatListNotice?, NoError> in')
    body=body.replace('if hidePremiumOffers || dismissedSuggestions.contains(ServerProvidedSuggestion.todayBirthdays.id)',
                      'if dismissedSuggestions.contains(ServerProvidedSuggestion.todayBirthdays.id)')
    assert body==old[old.index(marker):], 'Unrelated native priority, payment, dismiss or media path changed'
    signal=block(context,'private func nagramiXPremiumOffersHiddenSignal(')
    assert 'removeObserver(observer)' in signal and 'NagramiXPremiumOfferSettings.isHidden()' in signal
    assert 'in defaults:' not in signal, 'Do not capture a non-Sendable UserDefaults in notification callback'
    assert (source/runtime.BUILD).read_text()==previous(runtime.BUILD).replace('        "//submodules/TelegramCore",','        "//submodules/TelegramCore",\n        "//submodules/NagramiXCore:NagramiXCore",',1)
    assert 'GlobalControlPanelsContext' not in (source/'submodules/NagramiXCore/BUILD').read_text()
    return plan


def negatives(prefs,selection):
    def change(name,text,old,new,diagnostic):
        assert old in text,old
        return name,text.replace(old,new,1),diagnostic
    policy=block(selection,'private func nagramiXChatListSuggestions(')
    lost_others=selection.replace(policy,policy.replace('default:\n            return true','default:\n            return false'),1)
    return [
        change('cold-default-off',prefs,'as? Bool ?? true','as? Bool ?? false','cold install hides Premium banners'),
        change('saved-off-reset',prefs,'defaults.set(value, forKey: self.key)','defaults.set(true, forKey: self.key)','explicit OFF is preserved'),
        change('renewal-offer-leaks',selection,', .gracePremium:', ':','all five typed Premium promotions are hidden on first load'),
        change('birthday-gift-leaks',selection,'if hidePremiumOffers || dismissedSuggestions.contains','if dismissedSuggestions.contains','birthday gift banner is hidden without fetching its peers'),
        ('unrelated-notices-dropped',lost_others,'password setup warning is preserved'),
        change('missing-live-notification',selection,'if previous != value {','if previous == value {','live checkbox changes emit once without restart'),
        change('wrong-initial-checkbox',selection,'        subscriber.putNext(NagramiXPremiumOfferSettings.isHidden())\n        return ActionDisposable',
               '        subscriber.putNext(!NagramiXPremiumOfferSettings.isHidden())\n        return ActionDisposable','observer publishes cold default immediately'),
    ]


def cold_processes(swiftc,root,text):
    path=root/'cold.swift';path.write_text(text);results=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        binary=root/('cold-'+mode)
        run([swiftc,'-swift-version','5','-parse-as-library','-warnings-as-errors','-module-cache-path',root/'cache',*flags,path,'-o',binary])
        for action,value in [('read','true'),('write','false'),('read','false'),('write','true'),('read','true'),('read','true')]:
            run([binary,'nagramix.premium-offers.'+mode,action,value],timeout=30)
            results.append({'mode':mode,'action':action,'value':value,'passed':True})
        binary.unlink()
    return results


def public_api(swiftc,source,root):
    root.mkdir()
    model=root/'Core.swift';model.write_text('import Foundation\n'+block((source/runtime.TAB).read_text(),'public enum NagramiXPremiumOfferSettings {'))
    run([swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',root/'cache','-emit-module','-module-name','NagramiXCore',model,'-emit-module-path',root/'NagramiXCore.swiftmodule'])
    caller=root/'Caller.swift';caller.write_text('import Foundation\nimport NagramiXCore\nfunc accessSetting(_ value:Bool){_ = NagramiXPremiumOfferSettings.isHidden();NagramiXPremiumOfferSettings.setHidden(value);_ = NagramiXPremiumOfferSettings.changedNotification}\n')
    run([swiftc,'-swift-version','5','-warnings-as-errors','-module-cache-path',root/'cache','-typecheck','-I',root,caller])
    return 'production Foundation settings module and separate caller passed'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--swiftc',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();plan=contract(args.source);before=manifest(args.source)
    prefs=runtime.preferences(args.source);selection=runtime.selection(args.source)
    with tempfile.TemporaryDirectory(prefix='nagramix-premium-offers-') as temporary:
        root=Path(temporary);old_config=os.environ.get('XDG_CONFIG_HOME');os.environ['XDG_CONFIG_HOME']=str(root/'preferences')
        try:
            rejected=guard_checks(args.source,STAGE,plan,root/'guards')
            runs=execute(args.swiftc,root,'preferences',prefs)+execute(args.swiftc,root,'selection',selection)
            for name,text,diagnostic in negatives(prefs,selection):runs+=execute(args.swiftc,root,name,text,diagnostic)
            cold=cold_processes(args.swiftc,root,prefs);api=public_api(args.swiftc,args.source,root/'api')
            paths=[n for n in plan['outputs'] if n.endswith('.swift')]
            for name in paths:run([args.swiftc,'-frontend','-parse',args.source/name])
        finally:
            if old_config is None:os.environ.pop('XDG_CONFIG_HOME',None)
            else:os.environ['XDG_CONFIG_HOME']=old_config
    assert manifest(args.source)==before
    run(['python3',args.source/'build-system/Make/PostboxImportCheck.py',args.source])
    report={'stage':STAGE,'outputs':plan['outputs'],'guards':len(plan['guards']),'native_inputs':plan['native_inputs'],
            'fail_closed':len(rejected),'executions':runs,'cold_processes':cold,'public_api':api,'swift_parse':len(paths),
            'source_files':len(before),'source_unchanged_by_checks':True,'native_postbox_imports':'passed',
            'boundary':'Production preference, NotificationCenter observer, exact native notice-priority closure '
                       'and real SignalKit Atomic/Subscriber/Signal/Combine/Meta/Mapping execute. Peer, birthday, '
                       'StoreKit product and engine data/payment access are explicit adapters; Queue delivery is '
                       'immediate in tests. Real purchases, server suggestions, UIKit layout and Apple SDK '
                       'compilation are not proven.',
            'apple_sdk':'not_run','ipa':'not_built','physical_iphone':'pending'}
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('outputs','executions','cold_processes')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
