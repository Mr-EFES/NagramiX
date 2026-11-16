// Explicit UIKit/ContextUI/navigation IO hosts; actual settings/SignalKit and changed bodies execute.
public class UIView: NSObject {var window: NSObject?=NSObject()}
public class ContextGesture {}
public class ContextExtractedContentContainingView {let contentView=UIView()}
struct UIImage {init?(bundleImageName:String){}}
struct Theme {let contextMenu=Colors()}
struct Colors {let primaryColor=0}
func generateTintedImage(image:UIImage?,color:Int)->UIImage?{image}
class Strings {
 let Contacts_Title="Contacts",Calls_StartNewCall="Start new call",Calls_HideCallsTab="Hide Calls Tab"
 let catalogs:[String:String]
 init(_ catalogs:[String:String]){self.catalogs=catalogs}
 func nagramiXLocalized(_ key:String)->String{catalogs[key]!}
 // ACTUAL_STRING_GETTERS
}
struct PresentationData {let strings:Strings;let theme=Theme()}
class TabItem {var title:String?;var image:UIImage?;var selectedImage:UIImage?}
public class ViewController:NSObject {
 let tabBarItem=TabItem();var tabBarItemContextActionType=ContextKind.none
 var nativeContexts=0,searches=0;weak var navigationController:Navigation?
 func tabBarItemContextAction(sourceView:ContextExtractedContentContainingView,gesture:ContextGesture){nativeContexts+=1}
 func tabBarActivateSearch(){searches+=1}
}
enum ContextKind {case none,always}
class ContactsController:ViewController {
 // ACTUAL_CONTACTS_MODE
 var switchToChatsController:(()->Void)?
 private let presentationData:PresentationData
 init(context:Context,isTab:Bool=false){self.isTab=isTab;presentationData=context.data;super.init();nagramiXUpdateTabItem()}
 // ACTUAL_CONTACTS_TAB_ITEM
}
class CallsController:ViewController {}
class ChatsController:ViewController {}
class NewsController:ViewController {}
class SettingsController:ViewController {}
class Navigation {var pops=0;func popViewController(animated:Bool){pops+=1}}
class MainWindow {var lastMenu:ContextController?;func presentInGlobalOverlay(_ c:ContextController){lastMenu=c}}
class SharedContext {var mainWindow:MainWindow?=MainWindow()}
class Context {let sharedContext=SharedContext();let data:PresentationData;init(_ s:Strings){data=PresentationData(strings:s)}}
class ContextController {
 struct Items {let content:Content}
 enum Content {case list([ContextMenuItem])}
 let items:[ContextMenuItem]
 // Dismissal is an IO boundary: tests may delay its completion to model root replacement.
 static var heldDismissal:(()->Void)?
 static var holdDismissal=false
 init(_ items:[ContextMenuItem]){self.items=items}
 func dismiss(completion:@escaping ()->Void){if Self.holdDismissal{Self.heldDismissal=completion}else{completion()}}
}
enum ContextMenuItem {case action(ContextMenuActionItem)}
struct ContextMenuActionItem {
 let text:String;let icon:(Theme)->UIImage?;let action:(ContextController?,Int)->Void
}
protocol ContextReferenceContentSource {var keepInPlace:Bool{get};func transitionInfo()->ContextControllerReferenceViewInfo?}
enum ActionsPosition {case top}
struct ContextControllerReferenceViewInfo {let referenceView:UIView;let contentAreaInScreenSpace:CGRect;let actionsPosition:ActionsPosition}
let mainWindowScreenBounds=CGRect(x:0,y:0,width:390,height:844)
enum Source {case reference(ContextReferenceContentSource)}
func makeContextController(presentationData:PresentationData,source:Source,items:Signal<ContextController.Items,NoError>,recognizer:Int?,gesture:ContextGesture?)->ContextController{
 var result:[ContextMenuItem]=[]
 let d=items.start(next:{if case let .list(list)=$0.content{result=list}});d.dispose()
 return ContextController(result)
}
class TabBarNode {var tabBarItems:[ViewController]=[]}
class TabBarControllerImpl:ViewController {
 var controllers:[ViewController]=[],selectedIndex=0
 var currentController:ViewController?{controllers.indices.contains(selectedIndex) ? controllers[selectedIndex]:nil}
 let tabBarControllerNode=TabBarNode()
 var layoutUpdates=0
 var nagramiXGlobalSearchController:ViewController?
 var nagramiXActivateGlobalSearch:(()->Void)?
 // ACTUAL_TAB_HOOKS
 init(theme:Theme,strings:Strings){super.init()}
 var navigationPresentation=Presentation.master
 enum Presentation {case master}
 enum Transition {case immediate}
 func updateLayout(transition:Transition){layoutUpdates+=1}
 func setControllers(_ next:[ViewController],selectedIndex:Int?){
  let old=currentController;controllers=next;tabBarControllerNode.tabBarItems=next
  self.selectedIndex=selectedIndex ?? old.flatMap{old in next.firstIndex{$0===old}} ?? 0
 }
 func dispatchContext(index:Int,view:ContextExtractedContentContainingView,gesture:ContextGesture){
 let invoke = { [weak self] in
 // ACTUAL_TAB_DISPATCH
 }
 invoke()
 }
}
class Root:NSObject {
 let context:Context;var presentationData:PresentationData
 var rootTabController:ViewController?
 var bar:TabBarControllerImpl{rootTabController as! TabBarControllerImpl}
 var callListController:CallsController?,chatListController:ChatsController?,newsController:NewsController?,accountSettingsController:SettingsController?
 // ACTUAL_CONTACTS_OWNERSHIP
 private var nagramiXShowNewsTab=false
 var viewControllers:[ViewController]=[]
 private var observer:NSObjectProtocol?
 init(_ strings:Strings){
  context=Context(strings);presentationData=context.data;super.init()
  callListController=CallsController();chatListController=ChatsController();newsController=NewsController();accountSettingsController=SettingsController()
  let tabBarController=TabBarControllerImpl(theme:presentationData.theme,strings:strings)
  // ACTUAL_CONTACTS_CONSTRUCTION
  // ACTUAL_CONTACTS_BINDING
  rootTabController=tabBarController
  tabBarController.setControllers(nagramiXConfiguredControllers(),selectedIndex:nil);viewControllers=[tabBarController]
  observer=NotificationCenter.default.addObserver(forName:NagramiXTabSettings.changedNotification,object:nil,queue:nil){[weak self] _ in self?.applyNagramiXTabSettings()}
 }
 deinit{if let observer{NotificationCenter.default.removeObserver(observer)}}
 func openChatsController(activateSearch:Bool){if activateSearch{chatListController?.tabBarActivateSearch()}}
 func setViewControllers(_ values:[ViewController],animated:Bool){viewControllers=values}
 // Standalone screen creation is IO; the production openContacts body is guarded byte-for-byte.
 func pushStandaloneContacts()->ContactsController{let c=ContactsController(context:context);contactsController=c;return c}
 // ACTUAL_ROOT_METHODS
 func contactsIdentity()->ObjectIdentifier?{nagramiXContactsTabController.map{ObjectIdentifier($0)}}
 func makeNewsVisible(_ visible:Bool){nagramiXShowNewsTab=visible;applyNagramiXTabSettings()}
 func refresh(){applyNagramiXTabSettings()}
 func restart(){softRestartNagramiXTabInterface()}
}
enum GestureState {case began,changed,ended,cancelled}
class UILongPressGestureRecognizer {var state=GestureState.began;var isEnabled=false}
class SearchActions:UIView {
 struct Params {var isActive:Bool}
 var params:Params?=Params(isActive:false)
 var contextAction:((UIView)->Void)?
 var contextActionTitle:String?
 // ACTUAL_SEARCH_HANDLERS
 func longPress(_ state:GestureState){let g=UILongPressGestureRecognizer();g.state=state;onContextGesture(g)}
 func accessibleMenu()->Bool{onContextAccessibilityAction()}
}
enum TabBarComponent {
 // ACTUAL_SEARCH_MODEL
}
// ACTUAL_CONTACTS_BACK_ACTION
