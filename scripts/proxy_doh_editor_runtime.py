"""Реальные callbacks редактора DoH и история DNS в явных тестовых границах."""
from validate_quick_format import block
from round_video_editor_runtime import GEOMETRY_BOUNDARY

TAB='submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'
EDITOR='submodules/SettingsUI/Sources/NagramiXCustomDohController.swift'
UI='submodules/SettingsUI/Sources/Data and Storage/ProxyListSettingsController.swift'
ALERT='submodules/TelegramUI/Components/AlertComponent/Sources/AlertComponent.swift'

CHECK=r'''
var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("DoH regression: "+message+"\n").utf8));exit(91)};checks+=1}
'''


def history(source):
    text=(source/TAB).read_text()
    return GEOMETRY_BOUNDARY+CHECK+block(text,'public enum NagramiXDnsProvider:')+'\n'+block(text,'public enum NagramiXDnsProviderHistory {')+r'''
@main struct HistoryTests {static func main(){
 if CommandLine.arguments.count==4 {
  let defaults=UserDefaults(suiteName:CommandLine.arguments[1])!
  let expected=NagramiXDnsProvider(rawValue:Int(CommandLine.arguments[3])!)!
  if CommandLine.arguments[2]=="write" {
   NagramiXDnsProviderHistory.remember(previous:expected,current:.customDoh,in:defaults)
   check(defaults.synchronize(),"cold-process history write completes")
  } else {
   check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:.customDoh,in:defaults)==expected,"prior DNS survives a separate cold process")
  }
  print("PASS DoH cold process")
  return
 }
 let suite="nagramix-doh-test-"+UUID().uuidString
 let defaults=UserDefaults(suiteName:suite)!
 defer{defaults.removePersistentDomain(forName:suite)}
 let key="nagramix.network.dnsProviderBeforeCustomDoh"
 for previous in NagramiXDnsProvider.allCases where previous != .customDoh {
  defaults.removeObject(forKey:key)
  check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:previous,in:defaults)==previous,"delete before first save retains active DNS")
  NagramiXDnsProviderHistory.remember(previous:previous,current:.customDoh,in:defaults)
  check(defaults.object(forKey:key) as? Int == previous.rawValue,"exact prior provider ID including System zero is persisted")
  NagramiXDnsProviderHistory.remember(previous:.customDoh,current:.customDoh,in:defaults)
  check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:.customDoh,in:defaults)==previous,"editing custom URL preserves previous DNS")
  let reread=UserDefaults(suiteName:suite)!
  check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:.customDoh,in:reread)==previous,"history survives new defaults instance")
  for unrelated in NagramiXDnsProvider.allCases where unrelated != .customDoh {
   NagramiXDnsProviderHistory.remember(previous:unrelated,current:unrelated,in:defaults)
   check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:.customDoh,in:defaults)==previous,"unrelated settings update cannot overwrite history")
  }
 }
 for raw in [2,4,6,99,-1] {
  defaults.set(raw,forKey:key)
  check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:.customDoh,in:defaults) == .telegram,"invalid or custom history uses existing Telegram default")
 }
 defaults.removeObject(forKey:key)
 check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:.customDoh,in:defaults) == .telegram,"legacy custom install without history uses existing default")
 NagramiXDnsProviderHistory.remember(previous:.google,current:.customDoh,in:defaults)
 NagramiXDnsProviderHistory.remember(previous:.cloudflare,current:.customDoh,in:defaults)
 check(NagramiXDnsProviderHistory.providerAfterRemovingCustomDoh(current:.customDoh,in:defaults) == .cloudflare,"new custom session remembers most recent native DNS choice")
 print("PASS DoH history checks: \(checks)")
}}
'''


BOUNDARY=r'''
protocol Disposable {func dispose()}
final class ActionDisposable:Disposable {let action:()->Void;init(_ a:@escaping()->Void){action=a};func dispose(){action()}}
final class MetaDisposable:Disposable {var value:Disposable?;var disposed=false;func set(_ d:Disposable){if disposed{d.dispose()}else{value?.dispose();value=d}};func dispose(){disposed=true;value?.dispose();value=nil}}
struct NoError:Error {}
final class Subscriber<T,E> {let next:(T)->Void;let complete:()->Void;init(_ n:@escaping(T)->Void,_ c:@escaping()->Void){next=n;complete=c};func putNext(_ v:T){next(v)};func putCompletion(){complete()}}
final class Signal<T,E> {let body:(Subscriber<T,E>)->Disposable;init(_ b:@escaping(Subscriber<T,E>)->Disposable){body=b};func start(next:@escaping(T)->Void={_ in},completed:@escaping()->Void={})->Disposable{body(Subscriber(next,completed))};static func single(_ v:T)->Signal{Signal{s in s.putNext(v);s.putCompletion();return ActionDisposable{}}}}
infix operator |> : AdditionPrecedence
func |> <T,U>(v:T,f:(T)->U)->U{f(v)}
func map<T,U,E>(_ f:@escaping(T)->U)->(Signal<T,E>)->Signal<U,E>{{s in Signal<U,E>{out in s.start(next:{out.putNext(f($0))},completed:{out.putCompletion()})}}}
func take<T,E>(_ count:Int)->(Signal<T,E>)->Signal<T,E>{{s in Signal{out in var remaining=count;return s.start(next:{v in if remaining>0{remaining-=1;out.putNext(v)}},completed:{out.putCompletion()})}}}
func deliverOnMainQueue<T,E>(_ signal:Signal<T,E>)->Signal<T,E>{signal}
final class ValuePromise<T> {var value:T;init(_ v:T){value=v};func set(_ v:T){value=v};func get()->Signal<T,NoError>{.single(value)}}
final class EndpointRequest {var next:((Any)->Void)?;var completed:(()->Void)?;var failed:((Int)->Void)?;var disposed=false
 func start(next:@escaping(Any)->Void,error:@escaping(Int)->Void,completed:@escaping()->Void)->Disposable?{self.next=next;self.completed=completed;self.failed=error;return ActionDisposable{self.disposed=true}}
}
enum NagramiXDNSResolver {static var requests:[EndpointRequest]=[];static func testEndpoint(_ url:String,hostname:String)->EndpointRequest{let r=EndpointRequest();requests.append(r);return r}}
struct Strings {let nagramiXDnsCustom="Пользовательский DoH";let nagramiXCustomDohInvalid="Введите HTTPS URL";let nagramiXCustomDohPlaceholder="https://";let Common_Delete="Удалить";let nagramiXSave="Сохранить";let Common_OK="OK";let nagramiXCustomDohUnavailable="Unavailable"}
struct PresentationData {let strings=Strings()}
struct DataBox {func with<T>(_ f:(PresentationData)->T)->T{f(PresentationData())}}
struct SharedContext {let currentPresentationData=DataBox();let presentationData=0}
final class AccountContext {let sharedContext=SharedContext()}
class ViewController {enum Location{case window(Window)};enum Window{case root};var presented=0;func present(_ c:ViewController,in location:Location){presented+=1}}
enum AlertComponentEnvironment {}
struct AnyComponent {let value:Any;init(_ value:Any){self.value=value}}
struct AnyComponentWithIdentity<E> {let id:String;let component:AnyComponent}
struct AlertTitleComponent {let title:String}
struct AlertTextComponent {enum Content{case plain(String)};let content:Content}
final class AlertInputFieldComponent {
 final class ExternalState {var value="";var errors=0;var valueSignal:Signal<String,NoError>{Signal{s in s.putNext(self.value);return ActionDisposable{}}};func animateError(){errors+=1}}
 enum Keyboard{case URL};enum Capitalization{case none};enum Correction{case no}
 let state:ExternalState;let returnKeyAction:()->Void;let hasClearButton:Bool
 init(context:AccountContext,initialValue:String,placeholder:String,characterLimit:Int,hasClearButton:Bool,keyboardType:Keyboard,autocapitalizationType:Capitalization,autocorrectionType:Correction,isInitiallyFocused:Bool,externalState:ExternalState,shouldChangeText:(String)->Bool,returnKeyAction:@escaping()->Void){state=externalState;state.value=initialValue;self.returnKeyAction=returnKeyAction;self.hasClearButton=hasClearButton}
}
final class AlertScreen:ViewController {
 struct Configuration {let allowInputInset:Bool}
 struct Action {enum Kind{case generic,destructive,`default`};let title:String;let type:Kind;let action:()->Void;let autoDismiss:Bool;let isEnabled:Signal<Bool,NoError>;let progress:Signal<Bool,NoError>
 init(title:String,type:Kind = .generic,action:@escaping()->Void={},autoDismiss:Bool=true,isEnabled:Signal<Bool,NoError> = .single(true),progress:Signal<Bool,NoError> = .single(false)){self.title=title;self.type=type;self.action=action;self.autoDismiss=autoDismiss;self.isEnabled=isEnabled;self.progress=progress}}
 let actions:[Action];let content:[AnyComponentWithIdentity<AlertComponentEnvironment>];var dismissed:((Bool)->Void)?;var dismissals=0
 init(configuration:Configuration,content:[AnyComponentWithIdentity<AlertComponentEnvironment>],actions:[Action],updatedPresentationData:(PresentationData,Int)){self.content=content;self.actions=actions}
 func dismiss(){dismissals+=1;dismissed?(true)}
 var input:AlertInputFieldComponent{content[2].component.value as! AlertInputFieldComponent}
}
struct TextAlertAction {enum Kind{case defaultAction};init(type:Kind,title:String,action:()->Void){}}
func textAlertController(context:AccountContext,title:String?,text:String,actions:[TextAlertAction])->ViewController{ViewController()}
'''


def controller(source):
    text='\n'.join(l for l in (source/EDITOR).read_text().splitlines() if not l.startswith('import '))
    return GEOMETRY_BOUNDARY+CHECK+BOUNDARY+text+CONTROLLER_TESTS


CONTROLLER_TESTS=r'''
@main struct ControllerTests {static func main(){
 var saved:[String]=[];var removed=0
 func editor(_ initial:String="https://dns.example.org/dns-query")->AlertScreen {
  nagramiXCustomDohController(context:AccountContext(),initialValue:initial,apply:{saved.append($0)},clear:{removed+=1}) as! AlertScreen
 }
 for initial in ["","https://dns.example.org/dns-query"] {
  let c=editor(initial)
  check(c.actions.map{$0.title}==["Удалить","Сохранить"],"exactly Delete and Save even before first custom save")
  check(c.actions[0].type == .destructive && c.actions[1].type == .default,"native destructive and accent styles")
  check(c.content.map{$0.id}==["title","text","input"] && c.input.hasClearButton,"no header cross; native input cross remains")
  let before=removed;c.input.state.value=""
  check(removed==before && c.dismissals==0,"clearing input does not delete saved DNS or close editor")
  c.actions[0].action();c.actions[0].action()
  check(removed==before+1 && c.dismissals==1,"Delete commits and dismisses once")
 }
 let invalid=editor("http://dns.example.org")
 let count=NagramiXDNSResolver.requests.count;invalid.actions[1].action()
 check(NagramiXDNSResolver.requests.count==count && invalid.input.state.errors==1 && invalid.dismissals==0,"invalid URL never starts preflight or dismisses")
 let c=editor();let oldSaved=saved.count;c.actions[1].action();c.input.returnKeyAction()
 check(NagramiXDNSResolver.requests.count==count+1,"Save plus Return cannot start duplicate request")
 let first=NagramiXDNSResolver.requests.last!;first.next?("93.184.216.34");first.completed?()
 check(saved.count==oldSaved+1 && saved.last=="https://dns.example.org/dns-query" && c.dismissals==1,"successful Save applies validated URL and closes")
 c.actions[0].action();c.actions[1].action();check(c.dismissals==1,"no action can run after successful save")
 let pending=editor();pending.actions[1].action();let delayed=NagramiXDNSResolver.requests.last!;let before=saved.count
 pending.actions[0].action();delayed.next?("93.184.216.34");delayed.completed?()
 check(delayed.disposed && saved.count==before && pending.presented==0 && pending.dismissals==1,"Delete cancels pending test and rejects late Save success")
 let dismissed=editor();dismissed.actions[1].action();let outside=NagramiXDNSResolver.requests.last!;dismissed.dismiss()
 outside.next?("93.184.216.34");outside.completed?()
 check(outside.disposed && saved.count==before && dismissed.presented==0,"outside dismissal never applies a late response")
 let retry=editor();retry.actions[1].action();NagramiXDNSResolver.requests.last!.failed?(1)
 check(retry.dismissals==0 && retry.input.state.errors==1 && retry.presented==1,"unavailable endpoint leaves editor open and shows existing error")
 let attempts=NagramiXDNSResolver.requests.count;retry.actions[1].action()
 check(NagramiXDNSResolver.requests.count==attempts+1,"failure permits an explicit retry")
 NagramiXDNSResolver.requests.last!.next?("93.184.216.34")
 check(retry.dismissals==1 && saved.count==before+1,"retried Save applies once")
 for bad in ["", " https://dns.example.org", "https://dns.example.org ", "http://dns.example.org", "https://u:p@dns.example.org", "https://dns.exam ple.org"] {
  check(validatedNagramiXDohUrl(bad)==nil,"existing HTTPS validation preserved")
 }
 print("PASS DoH production controller checks: \(checks)")
}}
'''


def geometry(source):
    text=(source/ALERT).read_text()
    start=text.index('            let actionSideInset: CGFloat =')
    end=text.index('\n',text.index('            let halfWidthActionSize =',start))
    constants=text[start:end]
    start=text.index('                        itemFrame = CGRect(origin: CGPoint(x: actionOriginX, y: actionOriginY), size: halfWidthActionSize)')
    end=text.index('                    case .vertical:',start)
    horizontal=text[start:end]
    return GEOMETRY_BOUNDARY+CHECK+'''enum AlertActionComponent {static let actionHeight:CGFloat=50}
func frames(width alertWidth:CGFloat,count:Int)->[CGRect] {
'''+constants+'''
 var actionOriginX=actionSideInset
 let actionOriginY:CGFloat=0
 var result:[CGRect]=[]
 for _ in 0..<count { let itemFrame:CGRect
'''+horizontal+'''
 result.append(itemFrame)
 }
 _ = fullWidthActionSize
 return result
}
@main struct GeometryTests {static func main(){
 for width:CGFloat in [240,260,280,300,320,343,360,390,430] {
  let buttons=frames(width:width,count:2)
  check(buttons[0].minX==16 && buttons[1].maxX==width-16,"native two-button row has exact side margins")
  check(buttons[0].width==buttons[1].width && buttons[0].height==buttons[1].height,"buttons have equal size and baseline")
  check(buttons[0].maxX+8==buttons[1].minX,"buttons preserve native spacing")
  check(frames(width:width,count:3).last!.maxX>width,"old third horizontal button overflow is reproduced")
 }
 print("PASS DoH native button geometry checks: \\(checks)")
}}
'''
