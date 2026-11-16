private var checks=0
private func check(_ value:Bool,_ message:String){guard value else{print("FAIL: "+message);exit(96)};checks+=1}
private func count<T:ViewController>(_ type:T.Type,_ root:Root)->Int{root.bar.controllers.filter{$0 is T}.count}
private func invoke(_ menu:ContextController,_ index:Int){if case let .action(item)=menu.items[index]{item.action(menu,0)}}
private final class WeakRoot {weak var value:Root?}
@main private enum TabVisibilityTests {
 static func main(){
  let suite=ProcessInfo.processInfo.environment["NAGRAMIX_TEST_SUITE"]!
  let defaults=UserDefaults(suiteName:suite)!
  defaults.removePersistentDomain(forName:suite)
  defer{defaults.removePersistentDomain(forName:suite)}
  check(NagramiXTabSettings.current.hideContacts && NagramiXTabSettings.current.hideCalls && !NagramiXTabSettings.current.showSearchButton,"existing clean defaults preserved")
  let strings=Strings(actionCatalog)
  for wide in [false,true]{for hideContacts in [false,true]{for hideCalls in [false,true]{for search in [false,true]{
   NagramiXTabSettings.update{$0.wideTabBar=wide;$0.hideContacts=hideContacts;$0.hideCalls=hideCalls;$0.showSearchButton=search}
   let root=Root(strings),bar=root.bar
   check(count(ContactsController.self,root)==(hideContacts ? 0:1),"contacts follow the saved checkbox in both bar modes")
   check(count(CallsController.self,root)==(hideCalls ? 0:1),"calls follow the saved checkbox in both bar modes")
   check(count(ChatsController.self,root)==1 && count(SettingsController.self,root)==1,"essential tabs remain available")
   check(defaults.object(forKey:"nagramix.tabs.hideContacts") as? Bool == hideContacts && defaults.object(forKey:"nagramix.tabs.hideCalls") as? Bool == hideCalls,"both visibility flags persist under original keys")
   check(defaults.object(forKey:"nagramix.tabs.wideBar") as? Bool == wide && defaults.object(forKey:"nagramix.tabs.showSearchButton") as? Bool == search,"width and positive search setting persist independently")
   check(bar.nagramiXGlobalSearchController===root.chatListController,"global search retains the chat target")
   bar.nagramiXActivateGlobalSearch?();check(root.chatListController!.searches==1,"search activation uses the existing chat controller")
   let chatIndex=bar.controllers.firstIndex{$0===root.chatListController}!
   bar.dispatchContext(index:chatIndex,view:ContextExtractedContentContainingView(),gesture:ContextGesture())
   check(root.chatListController!.nativeContexts==1,"unhandled tab menus keep native dispatch")
   root.makeNewsVisible(true);check(count(NewsController.self,root)==1,"news tab eligibility survives filtering")
   root.makeNewsVisible(false)
   let identity=root.contactsIdentity()
   let standalone=root.pushStandaloneContacts()
   check(!standalone.isTab && root.contactsIdentity()==identity,"pushed Contacts does not replace the tab cache")
   NagramiXTabSettings.update{$0.hideContacts=false}
   check(count(ContactsController.self,root)==1,"hidden contacts can always be restored")
   check(bar.controllers.compactMap{$0 as? ContactsController}.first!.isTab,"root Contacts uses tab presentation")
   check(bar.controllers.compactMap{$0 as? ContactsController}.first!.tabBarItem.title=="Contacts","contacts tab has its localized title")
   check(bar.controllers.compactMap{$0 as? ContactsController}.first!.tabBarItem.image != nil,"contacts tab has its real bundled icon")
   NagramiXTabSettings.update{$0.hideContacts=true}
   NagramiXTabSettings.update{$0.hideContacts=false}
   check(root.contactsIdentity()==identity && count(ContactsController.self,root)==1,"contacts survives hide/show without a new controller")
   root.restart();check(root.contactsIdentity()==identity && count(ContactsController.self,root)==1,"soft restart keeps the retained Contacts tab")
   check(NagramiXTabSettings.current.wideTabBar==wide,"tab visibility never flips the bar style")
  }}}}
  NagramiXTabSettings.update{$0.hideContacts=false;$0.hideCalls=false;$0.showSearchButton=true}
  let root=Root(strings)
  for type in [ContactsController.self as ViewController.Type,CallsController.self as ViewController.Type]{
   let bar=root.bar
   let index=bar.controllers.firstIndex{type == ContactsController.self ? $0 is ContactsController:$0 is CallsController}!
   bar.selectedIndex=index
   bar.dispatchContext(index:index,view:ContextExtractedContentContainingView(),gesture:ContextGesture())
   let menu=root.context.sharedContext.mainWindow!.lastMenu!
   check(menu.items.count==(type == ContactsController.self ? 1:2),"calls retain New call; contacts get a hide action")
   if type == CallsController.self {invoke(menu,0);check(root.callListController!.searches==1,"native New call command preserved")}
   invoke(menu,menu.items.count-1)
   check(type == ContactsController.self ? NagramiXTabSettings.current.hideContacts:NagramiXTabSettings.current.hideCalls,"long press sets the same hide checkbox")
   check(root.bar.currentController===root.chatListController,"hiding the selected tab falls back to Chats by identity")
  }
  let searchBar=root.bar
  searchBar.nagramiXSearchContextAction?(UIView())
  let searchMenu=root.context.sharedContext.mainWindow!.lastMenu!
  check(searchMenu.items.count==1,"search has exactly the hide action")
  invoke(searchMenu,0)
  check(!NagramiXTabSettings.current.showSearchButton,"Hide search disables the positive Show search checkbox")
  let settings=ValuePromise(NagramiXTabSettings.current,ignoreRepeated:false)
  var settingsEvents:[NagramiXTabSettings]=[]
  let disposable=nagramiXLiveTabSettings(settings).start(next:{settingsEvents.append($0)})
  NagramiXTabSettings.update{$0.showSearchButton=true;$0.hideCalls=false}
  RunLoop.current.run(until:Date().addingTimeInterval(0.02))
  check(settingsEvents.last?.showSearchButton==true && settingsEvents.last?.hideCalls==false,"already-open settings follows external menu changes")
  let before=settingsEvents.count;settings.set(NagramiXTabSettings.current)
  RunLoop.current.run(until:Date().addingTimeInterval(0.02))
  check(settingsEvents.count>before,"explicit refresh still updates unrelated computed settings")
  disposable.dispose();let afterDispose=settingsEvents.count
  NagramiXTabSettings.update{$0.hideCalls=true}
  RunLoop.current.run(until:Date().addingTimeInterval(0.02))
  check(settingsEvents.count==afterDispose,"disposed settings removes notification/subscription ownership")
  let action=SearchActions();var menus=0;action.contextAction={_ in menus+=1}
  for state in [GestureState.ended,.changed,.cancelled]{action.longPress(state)}
  check(menus==0,"only a begun long press opens the search menu")
  action.longPress(.began);check(menus==1,"circle long press forwards to the root menu")
  check(action.accessibleMenu() && menus==2,"VoiceOver custom action opens the same menu")
  action.params=SearchActions.Params(isActive:true);action.longPress(.began)
  check(!action.accessibleMenu() && menus==2,"active text search keeps its editing gestures")
  action.params=SearchActions.Params(isActive:false);action.contextAction=nil
  check(!action.accessibleMenu(),"other search instances do not gain a dead context action")
  let plain=TabBarComponent.Search(isActive:false,activate:{},deactivate:{})
  let withMenu=TabBarComponent.Search(isActive:false,activate:{},deactivate:{},contextActionTitle:"Hide",contextAction:{_ in})
  check(plain != withMenu,"search equality notices menu availability")
  let renamed=TabBarComponent.Search(isActive:false,activate:{},deactivate:{},contextActionTitle:"Other",contextAction:{_ in})
  check(withMenu != renamed,"search equality notices localized action title")
  let standalone=ContactsController(context:root.context),tab=ContactsController(context:root.context,isTab:true)
  let navigation=Navigation();standalone.navigationController=navigation;tab.navigationController=navigation
  check(contactsBackAction(tab)==nil,"tab Contacts has no pushed-screen back action")
  contactsBackAction(standalone)?();check(navigation.pops==1,"standalone Contacts retains native Back")
  ContextController.holdDismissal=true
  root.bar.nagramiXSearchContextAction?(UIView())
  invoke(root.context.sharedContext.mainWindow!.lastMenu!,0)
  root.restart();ContextController.heldDismissal?();ContextController.holdDismissal=false;ContextController.heldDismissal=nil
  check(NagramiXTabSettings.current.showSearchButton,"menu from a replaced root cannot alter current settings")
  let weakRoot=WeakRoot()
  do{let temporary=Root(strings);weakRoot.value=temporary;temporary.bar.nagramiXSearchContextAction?(UIView())}
  check(weakRoot.value==nil,"root callbacks and menus do not retain the old account root")
  print("PASS actual tab visibility/menu/settings/lifecycle checks: \(checks)")
 }
}
