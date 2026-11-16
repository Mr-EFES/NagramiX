"""Real Core/SignalKit plus extracted production ownership/menu/notification/gesture bodies."""
from pathlib import Path
import json,os,subprocess,sys
from validate_quick_format import block
from original_video_mode_runtime import signal_library
ROOT=Path(__file__).resolve().parents[1]
ROOT_UI='submodules/TelegramUI/Sources/TelegramRootController.swift'
SETTINGS='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
BAR='submodules/TabBarUI/Sources/TabBarController.swift'
NODE='submodules/TabBarUI/Sources/TabBarContollerNode.swift'
COMPONENT='submodules/TelegramUI/Components/TabBarComponent/Sources/TabBarComponent.swift'
CONTACTS='submodules/ContactListUI/Sources/ContactsController.swift'
CONTACT_NODE='submodules/ContactListUI/Sources/ContactsControllerNode.swift'
CORE='submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'
STRINGS='submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift'

def modules(source,swiftc,folder,flags=(),cache=None):
    folder.mkdir(parents=True,exist_ok=True)
    common=[str(swiftc),'-swift-version','5','-warnings-as-errors','-parse-as-library','-module-cache-path',str(cache or folder/'cache'),*flags]
    suffix='.dylib' if sys.platform=='darwin' else '.so'
    def run(args):
        p=subprocess.run(common+[str(x) for x in args],capture_output=True,text=True,timeout=180)
        assert p.returncode==0,p.stdout+p.stderr
    media=sorted((source/'submodules/NagramiXMediaSettings/Sources').glob('*.swift'))
    assert media and any(p.name=='NagramiXMediaSettings.swift' for p in media)
    run(['-emit-module','-emit-library','-module-name','NagramiXMediaSettings',*media,'-emit-module-path',folder/'NagramiXMediaSettings.swiftmodule','-o',folder/('libNagramiXMediaSettings'+suffix)])
    core=folder/'core.swift'
    core.write_text('import Foundation\nprivate let fixtureCoreDefaults=UserDefaults(suiteName:ProcessInfo.processInfo.environment["NAGRAMIX_TEST_SUITE"]!)!\n'+(source/CORE).read_text().replace('UserDefaults.standard','fixtureCoreDefaults'))
    run(['-emit-module','-emit-library','-module-name','NagramiXCore','-I',folder,'-L',folder,'-lNagramiXMediaSettings',core,'-emit-module-path',folder/'NagramiXCore.swiftmodule','-o',folder/('libNagramiXCore'+suffix)])
    env=dict(os.environ);env['NAGRAMIX_TEST_SUITE']='NagramiX.TabVisibility.'+folder.name;env['XDG_CONFIG_HOME']=str(folder/'defaults')
    key='DYLD_LIBRARY_PATH' if sys.platform=='darwin' else 'LD_LIBRARY_PATH'
    env[key]=str(folder)+(':'+env[key] if env.get(key) else '')
    return ['-I',str(folder),'-L',str(folder),'-lNagramiXCore','-lNagramiXMediaSettings'],env

def fixture(source):
    code='import Foundation\nimport NagramiXCore\n'+signal_library(source)+'\n'
    if 'class Bag<' not in code and 'struct Bag<' not in code:code+=(source/'submodules/SSignalKit/SwiftSignalKit/Source/Bag.swift').read_text()
    code+='\n'+(source/'submodules/SSignalKit/SwiftSignalKit/Source/Promise.swift').read_text()+'\n'
    root=(source/ROOT_UI).read_text();contacts=(source/CONTACTS).read_text();bar=(source/BAR).read_text();component=(source/COMPONENT).read_text()
    host=(ROOT/'scripts/tests/NagramiXTabVisibilityBoundary.swift').read_text()
    getters='\n'.join(l for l in (source/STRINGS).read_text().splitlines() if 'var nagramiXHideContactsAction:' in l or 'var nagramiXHideSearchAction:' in l)
    dispatch=bar.split('}, contextAction: { [weak self] index, view, gesture in',1)[1].split('}, swipeAction:',1)[0]
    construction=root.split('        let contactsController = ContactsController(context: self.context, isTab: true)',1)[1].split('        var restoreSettignsController:',1)[0]
    construction='let contactsController = ContactsController(context: self.context, isTab: true)'+construction
    binding='\n'.join(l for l in block(root,'    public func addRootControllers(').splitlines() if l.strip().startswith(('self.contactsController =','self.nagramiXContactsTabController =')))
    back=(source/CONTACT_NODE).read_text().split('        let backPressed: (() -> Void)? =',1)[1].split('        let primaryContent',1)[0]
    pieces={
      'ACTUAL_STRING_GETTERS':getters,
      'ACTUAL_CONTACTS_MODE':next(l for l in contacts.splitlines() if 'public let isTab:' in l),
      'ACTUAL_CONTACTS_TAB_ITEM':block(contacts,'    private func nagramiXUpdateTabItem('),
      'ACTUAL_TAB_HOOKS':'\n'.join(l for l in bar.splitlines() if 'public var nagramiXTabContextAction:' in l or 'public var nagramiXSearchContextAction:' in l),
      'ACTUAL_TAB_DISPATCH':dispatch,
      'ACTUAL_CONTACTS_OWNERSHIP':'\n'.join(l for l in root.splitlines() if l.strip().startswith(('private weak var contactsController:','private var nagramiXContactsTabController:'))),
      'ACTUAL_CONTACTS_CONSTRUCTION':construction,
      'ACTUAL_CONTACTS_BINDING':binding,
      'ACTUAL_ROOT_METHODS':'\n'.join(('    @discardableResult\n' if 'nagramiXPresentTabMenu' in m else '')+block(root,m) for m in ['    private func nagramiXConfiguredControllers(', '    private func nagramiXPresentTabMenu(', '    private func applyNagramiXTabSettings(', '    private func softRestartNagramiXTabInterface(']),
      'ACTUAL_SEARCH_HANDLERS':'\n'.join(block(component,m).replace('@objc ','') for m in ['    @objc private func onContextGesture(', '    @objc private func onContextAccessibilityAction(']),
      'ACTUAL_SEARCH_MODEL':block(component,'    public final class Search:'),
      'ACTUAL_CONTACTS_BACK_ACTION':'func contactsBackAction(_ controller:ContactsController?)->(()->Void)?{struct Host {let controller:ContactsController?};let selfHost=Host(controller:controller)\n let backPressed:(()->Void)? ='+back.replace('self.controller','selfHost.controller').replace('{ [weak self] in\n            self?.controller?.navigationController?.popViewController(animated: true)\n        }','{ selfHost.controller?.navigationController?.popViewController(animated: true) }')+'\nreturn backPressed\n}',
    }
    # Preserve the real ownership declarations; changed bodies remain inside their original classes.
    for key,value in pieces.items():assert host.count('// '+key)==1,key;host=host.replace('// '+key,value,1)
    code+=host+'\n'+block(root,'private final class NagramiXTabMenuSource:')+'\n'
    code+=block((source/SETTINGS).read_text(),'private func nagramiXLiveTabSettings(')+'\n'
    catalogs=json.loads((ROOT/'ios/tab_visibility_sync/localization.json').read_text())
    code+='let actionCatalog:[String:String] = '+str(dict(zip(catalogs['keys'],catalogs['translations']['en']))).replace("'",'"').replace('{','[').replace('}',']')+'\n'
    code+=(ROOT/'scripts/tests/NagramiXTabVisibilityTests.swift').read_text()
    return code
