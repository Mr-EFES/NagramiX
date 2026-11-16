#!/usr/bin/env python3
"""Проверить единое состояние вкладок, удержание Контактов и меню поиска."""
import argparse,hashlib,json,resource,subprocess,tempfile
from pathlib import Path
from late_source_stages import LATE_SOURCE_STAGES,verified_prefix
from validate_quick_format import block,manifest
from validate_upstream_13_2_release import checked_plan,guard_checks,OVERLAY
from validate_private_temporary_transcription import save_failed_fixture
from validate_app_language_localization import strings
from tab_visibility_apple import check as apple_check
import tab_visibility_runtime as rt
STAGE='tab_visibility_sync'

def contracts(source):
    plan=checked_plan(STAGE)
    assert len(plan['inputs'])==79 and len(plan['guards'])==22 and not plan['copies'] and not plan['deletions']
    assert plan['required_previous_stage']=='round_video_encoding'
    for name,markers,remove in [
      (rt.ROOT_UI,['    public init(context:', '    private func nagramiXConfiguredControllers(', '    public func addRootControllers('], ['import ContextUI\n','    private var nagramiXContactsTabController: ContactsController?\n']),
      (rt.BAR,['    override open func loadDisplayNode('], ['    public var nagramiXTabContextAction: ((ViewController, ContextExtractedContentContainingView, ContextGesture) -> Bool)?\n','    public var nagramiXSearchContextAction: ((UIView) -> Void)?\n']),
      (rt.NODE,['    private func updateImpl('], ['    private let nagramiXSearchContextAction: () -> ((UIView) -> Void)?\n','        self.nagramiXSearchContextAction = nagramiXSearchContextAction\n']),
      (rt.CONTACTS,['    public init(context:', '    private func updateThemeAndStrings('], ['    public let isTab: Bool\n']),
      (rt.CONTACT_NODE,['    func updateNavigationBar('], []),
      (rt.COMPONENT,['public final class NavigationSearchView:', '    public final class Search:'], ['                searchView.contextAction = search.contextAction\n','                searchView.contextActionTitle = search.contextActionTitle\n']),
    ]:
        before=(OVERLAY/plan['previous'][name]).read_text();after=(source/name).read_text();restored=after
        for marker in markers:restored=restored.replace(block(after,marker),block(before,marker),1)
        for value in remove:assert restored.count(value)==1,(name,value);restored=restored.replace(value,'',1)
        if name==rt.ROOT_UI:
            restored=restored.replace('    @discardableResult\n'+block(after,'    private func nagramiXPresentTabMenu(')+'\n\n','',1)
            restored=restored.replace('\n'+block(after,'private final class NagramiXTabMenuSource:')+'\n','',1)
        if name==rt.CONTACTS:restored=restored.replace(block(after,'    private func nagramiXUpdateTabItem(')+'\n\n','',1)
        if name==rt.NODE:restored=restored.replace(', nagramiXSearchContextAction: @escaping () -> ((UIView) -> Void)? = { nil }','',1)
        assert restored==before,'Unrelated runtime changed: '+name
    before=(OVERLAY/plan['previous'][rt.SETTINGS]).read_text();after=(source/rt.SETTINGS).read_text()
    restored=after.replace(block(after,'private func nagramiXLiveTabSettings(')+'\n\n','',1).replace('combineLatest(nagramiXLiveTabSettings(settingsPromise),','combineLatest(settingsPromise.get(),',1)
    assert restored==before,'Settings rows/IDs or callbacks changed'
    after=(source/rt.STRINGS).read_text();restored='\n'.join(l for l in after.split('\n') if 'var nagramiXHideContactsAction:' not in l and 'var nagramiXHideSearchAction:' not in l)
    assert restored==(OVERLAY/plan['previous'][rt.STRINGS]).read_text()
    loc=json.loads((OVERLAY/'tab_visibility_sync/localization.json').read_text())
    codes={x['code'] for x in json.loads((OVERLAY/'app_language_localization/languages.json').read_text())['languages']}
    assert set(loc['translations'])==codes and len(codes)==71
    for code in codes:
        n=f'submodules/NagramiXCore/Resources/{code}.lproj/Localizable.strings';old=strings(OVERLAY/plan['previous'][n]);new=strings(source/n)
        assert len(old)==678 and len(new)==680 and new=={**old,**dict(zip(loc['keys'],loc['translations'][code]))},code
    root=(source/rt.ROOT_UI).read_text();bar=(source/rt.BAR).read_text();component=(source/rt.COMPONENT).read_text()
    assert 'private var nagramiXContactsTabController:' in root
    assert 'nagramiXContactsTabController =' not in block(root,'    public func openContacts(')
    assert 'if !settings.hideContacts' in root and 'if !settings.hideCalls' in root
    assert 'isTab: true' in block(root,'    public func addRootControllers(')
    contacts=(source/rt.CONTACTS).read_text()
    for marker in ['    public init(context:', '    private func updateThemeAndStrings(']:
        assert 'self.nagramiXUpdateTabItem()' in block(contacts,marker)
    assert 'public init(context: AccountContext, isTab: Bool = false)' in contacts
    assert 'UIImage(bundleImageName: "Chat List/Tabs/IconContacts")' in block(contacts,'    private func nagramiXUpdateTabItem(')
    icon=source/'submodules/TelegramUI/Images.xcassets/Chat List/Tabs/IconContacts.imageset/Contents.json'
    if icon.exists():
        images=json.loads(icon.read_text())['images']
        assert any((icon.parent/item['filename']).is_file() for item in images if 'filename' in item)
    assert block(root,'    public func updateRootControllers(')==block((OVERLAY/plan['previous'][rt.ROOT_UI]).read_text(),'    public func updateRootControllers(')
    assert '!= true' in block(bar,'    override open func loadDisplayNode(')
    assert 'self.contextGesture.isEnabled = self.contextAction != nil && !isActive' in component
    assert 'searchView.contextAction = search.contextAction' in component
    for build in ['submodules/TelegramUI/BUILD','submodules/TabBarUI/BUILD','submodules/ContactListUI/BUILD','submodules/TelegramUI/Components/TabBarComponent/BUILD']:
        guarded=(OVERLAY/plan['guard_sources'][build]).read_bytes()
        if (source/build).exists():assert (source/build).read_bytes()==guarded
    assert '"//submodules/ContextUI:ContextUI"' in (OVERLAY/plan['guard_sources']['submodules/TelegramUI/BUILD']).read_text()
    return {'unchanged_original_keys_defaults_and_persistence':True,'native_calls_flag_does_not_override_nagramix_visibility':True,'root_tabs_and_search_menu_share_checkbox_values':True,'contacts_retained_separately_from_pushed_screen':True,'calls_new_call_and_other_native_menus_preserved':True,'selected_tab_falls_back_by_identity':True,'other_geometry_and_bar_mode_unchanged':True,'settings_live_observer_disposed_with_subscription':True,'new_localization_keys':2,'languages':71,'key_count':680}

def check(source,swiftc,folder):
    folder.mkdir(parents=True,exist_ok=True);contract=contracts(source);code=rt.fixture(source)
    variants=[
      ('weak-contacts','private var nagramiXContactsTabController:','private weak var nagramiXContactsTabController:','contacts survives hide/show'),
      ('inverted-contacts','if !settings.hideContacts,','if settings.hideContacts,','contacts follow the saved checkbox'),
      ('inverted-calls','if !settings.hideCalls,','if settings.hideCalls,','calls follow the saved checkbox'),
      ('wrong-calls-checkbox','if isCalls { settings.hideCalls = true }','if isCalls { settings.hideCalls = false }','long press sets the same hide checkbox'),
      ('wrong-search-polarity','if isSearch { settings.showSearchButton = false }','if isSearch { settings.showSearchButton = true }','Hide search disables the positive'),
      ('missing-live-signal','forName: NagramiXTabSettings.changedNotification, object: nil, queue: nil','forName: Notification.Name("IgnoredTabSettings"), object: nil, queue: nil','already-open settings follows external'),
      ('native-fallback','strongSelf.nagramiXTabContextAction?(controller, view, gesture) != true','strongSelf.nagramiXTabContextAction?(controller, view, gesture) == true','unhandled tab menus keep native dispatch'),
      ('stale-root','self.rootTabController === rootTabController else { return }\n                NagramiXTabSettings.update','self.rootTabController === rootTabController || rootTabController.controllers.isEmpty else { return }\n                NagramiXTabSettings.update','menu from a replaced root cannot alter'),
      ('search-cache','lhs.isActive != rhs.isActive || lhs.contextActionTitle != rhs.contextActionTitle || (lhs.contextAction == nil) != (rhs.contextAction == nil)','lhs.isActive != rhs.isActive','search equality notices menu availability'),
    ]
    positive=[];negative=[]
    for mode,flags in [('debug',[]),('optimized',['-O'])]:
        runfolder=folder/mode;runfolder.mkdir()
        link,env=rt.modules(source,swiftc,runfolder/'modules',flags,cache=folder/'cache')
        def execute(name,text,diagnostic=None):
            p=runfolder/(name+'.swift');p.write_text(text);binary=runfolder/name
            args=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-module-cache-path',str(folder/'cache'),*flags,*link,str(p),'-o',str(binary)]
            compiled=subprocess.run(args,capture_output=True,text=True,timeout=180)
            if compiled.returncode:save_failed_fixture(p,name,mode,'compile',compiled)
            assert compiled.returncode==0,compiled.stdout+compiled.stderr
            result=subprocess.run([str(binary)],env=env,capture_output=True,text=True,timeout=60,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            output=(result.stdout+result.stderr).strip();valid=result.returncode==0 if diagnostic is None else result.returncode==96 and diagnostic in output
            if not valid:save_failed_fixture(p,name,mode,'runtime',result)
            assert valid,(name,mode,result.returncode,output)
            binary.unlink()
            return {'name':name,'mode':mode,'exit_code':result.returncode,'output':output}
        positive.append(execute('tab-visibility',code))
        for name,old,new,reason in variants:
            assert code.count(old)==1,(name,code.count(old));negative.append(execute(name,code.replace(old,new,1),reason))
    return {'contracts':contract,'executions':positive,'semantic_negatives':negative,'apple_api':apple_check(source,swiftc,folder/'apple'),'boundary':'Actual Core/media settings modules and real SignalKit; extracted production filtering, ownership, menu actions, native fallback, settings signal and search handlers/model execute. UIKit, navigation, menu presentation/dismissal and construction of unchanged controllers are explicit IO hosts. No pixel/iPhone verification claimed.','full_application_sdk':'not_run','physical_iphone':'pending'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
    assert verified_prefix(a.source)==LATE_SOURCE_STAGES.index(STAGE)+1
    initial=manifest(a.source);plan=checked_plan(STAGE)
    with tempfile.TemporaryDirectory(prefix='nagramix-tab-visibility-') as d:
        folder=Path(d);refused=guard_checks(a.source,STAGE,plan,folder/'guards');result=check(a.source,a.swiftc,folder/'runtime')
        for name in plan['inputs']:
            if name.endswith('.swift'):
                parsed=subprocess.run([str(a.swiftc),'-frontend','-parse',str(a.source/name)],capture_output=True,text=True,timeout=120);assert parsed.returncode==0,parsed.stdout+parsed.stderr
    assert manifest(a.source)==initial
    report={'stage':103,'name':STAGE,'runtime_swift_files':8,'localized_catalogs':71,'guards':22,'loader_refusals':len(refused),'checks':result,'source_unchanged_by_checks':True,'new_actions_or_ipa_started':False}
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
