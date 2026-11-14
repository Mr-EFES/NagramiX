"""Реальный редактор DoH и SwiftSignalKit; UIKit и transport — явные границы."""
import json
import re
from pathlib import Path
from validate_quick_format import block
from validate_upstream_13_2_release import checked_plan, OVERLAY
from validate_app_language_localization import strings

EDITOR = 'submodules/SettingsUI/Sources/NagramiXCustomDohController.swift'
ALERT = 'submodules/TelegramUI/Components/AlertComponent/Sources/AlertComponent.swift'
INPUT = 'submodules/TelegramUI/Components/AlertComponent/AlertInputFieldComponent/Sources/AlertInputFieldComponent.swift'
SK = 'submodules/SSignalKit/SwiftSignalKit/Source/'
CORE_STRINGS = 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift'
RU = 'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings'
NATIVE_RU = 'Telegram/Telegram-iOS/ru.lproj/Localizable.strings'


def source_text(source, name):
    path = source / name
    if path.is_file():
        return path.read_text()
    plan = checked_plan('doh_empty_action')
    return (OVERLAY / plan['guard_sources'][name]).read_text()


def native_value(source, key):
    # Vendor catalogs also contain non-JSON escapes in unrelated entries.
    # Read only these existing plain labels; do not reinterpret the full file.
    text = source_text(source, NATIVE_RU)
    values = re.findall(r'^"' + re.escape(key) + r'"\s*=\s*"((?:[^"\\]|\\.)*)";', text, re.M)
    assert len(values) == 1, key
    return json.loads('"' + values[0] + '"')


def library(source):
    result = 'import Foundation\n'
    for name in ['Atomic.swift', 'Disposable.swift', 'Subscriber.swift', 'Bag.swift']:
        result += '\n' + source_text(source, SK + name)
    result += '\n' + source_text(source, SK + 'Signal.swift').split('@available(iOS 13.0, macOS 10.15, *)', 1)[0]
    queue = source_text(source, SK + 'Queue.swift')
    # Only the legacy Dispatch closure boundary is adapted to Swift6 WorkItem.
    for old, new in [
        ('self.nativeQueue.async(execute: f)', 'self.nativeQueue.async(execute: DispatchWorkItem(block: f))'),
        ('self.nativeQueue.async(group: nil, qos: qos, flags: [.enforceQoS], execute: f)', 'self.nativeQueue.async(execute: DispatchWorkItem(qos: qos, flags: [.enforceQoS], block: f))'),
        ('self.nativeQueue.asyncAfter(deadline: time, execute: f)', 'self.nativeQueue.asyncAfter(deadline: time, execute: DispatchWorkItem(block: f))'),
    ]:
        assert old in queue
        queue = queue.replace(old, new)
    result += '\n' + queue
    for name, marker in [
        ('Promise.swift', 'public final class ValuePromise<T: Equatable>'),
        ('Signal_Mapping.swift', 'public func map<T, E, R>'),
        ('Signal_Mapping.swift', 'private class DistinctUntilChangedContext<T>'),
        ('Signal_Mapping.swift', 'public func distinctUntilChanged<T: Equatable, E>'),
        ('Signal_Take.swift', 'public func take<T, E>(_ count:'),
        ('Signal_Dispatch.swift', 'public func deliverOn<T, E>(_ queue: Queue)'),
        ('Signal_Dispatch.swift', 'public func deliverOnMainQueue<T, E>'),
    ]:
        result += '\n' + block(source_text(source, SK + name), marker)
    return result


def fixture(source):
    plan = checked_plan('doh_empty_action')
    catalogs = {RU: strings(source / RU if (source / RU).is_file() else OVERLAY / plan['guard_sources'][RU])}
    getters = ['nagramiXDnsCustom', 'nagramiXCustomDohInvalid', 'nagramiXCustomDohPlaceholder', 'nagramiXSave', 'nagramiXCustomDohUnavailable']
    catalog = {key: value for key, value in catalogs[RU].items() if key in [
        'NagramiX.Network.DNS.Custom', 'NagramiX.Network.DNS.CustomInvalid',
        'NagramiX.Network.DNS.CustomPlaceholder', 'NagramiX.Common.Save', 'NagramiX.Network.DNS.CustomUnavailable',
    ]}
    code = library(source)
    code += '\nstruct PresentationStrings {\n'
    for member, key in [('Common_Delete', 'Common.Delete'), ('WebApp_Download_Cancel', 'WebApp.Download.Cancel'), ('Common_OK', 'Common.OK')]:
        code += f'let {member} = {json.dumps(native_value(source, key), ensure_ascii=False)}\n'
    code += 'func nagramiXLocalized(_ key:String)->String {\nlet catalog:[String:String] = [' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + json.dumps(v, ensure_ascii=False) for k, v in catalog.items()) + ']\nreturn catalog[key]!\n}\n}\n'
    code += 'extension PresentationStrings {\n' + '\n'.join(block(source_text(source, CORE_STRINGS), 'var ' + member + ': String') for member in getters) + '\n}\n'
    code += BOUNDARY_PREFIX
    native = source_text(source, ALERT)
    code += 'final class AlertScreen: ViewController {\n'
    for marker in ['public enum ActionAligmnent:', 'public struct Configuration:', 'public struct Action:']:
        code += block(native, marker) + '\n'
    initializer = block(native, '    public init(\n        configuration: Configuration')
    code += ALERT_STORAGE + initializer.split('    ) {', 1)[0] + '    ) {\n' + ALERT_INIT + '\n}\n'
    code += block(native, '    public convenience init(\n        configuration: Configuration = Configuration(),\n        content:')
    code += ALERT_METHODS + '\n}\n'
    external = block(source_text(source, INPUT), '    public class ExternalState {')
    code += 'final class AlertInputFieldComponent {\n' + external + INPUT_BOUNDARY + '\n}\n'
    production = '\n'.join(line for line in (source / EDITOR).read_text().splitlines() if not line.startswith('import '))
    return code + '\n' + production + '\n' + TESTS


BOUNDARY_PREFIX = r'''
private var checks=0
private func check(_ value:@autoclosure()->Bool,_ message:String){
 if !value(){print("FAIL: "+message);exit(96)};checks+=1
}
struct PresentationData {let strings=PresentationStrings()}
struct DataBox {func with<T>(_ f:(PresentationData)->T)->T{f(PresentationData())}}
struct SharedContext {let currentPresentationData=DataBox();let presentationData:Signal<PresentationData,NoError> = .single(PresentationData())}
final class AccountContext {let sharedContext=SharedContext()}
class ViewController {enum Location{case window(Window)};enum Window{case root};var presented=0;func present(_ c:ViewController,in location:Location){presented+=1}}
enum AlertComponentEnvironment {}
struct AnyComponent {let value:Any;init(_ value:Any){self.value=value}}
struct AnyComponentWithIdentity<E> {let id:String;let component:AnyComponent}
struct AlertTitleComponent {let title:String}
struct AlertTextComponent {enum Content{case plain(String)};let content:Content}
struct TextAlertAction {enum Kind{case defaultAction};init(type:Kind,title:String,action:()->Void){}}
func textAlertController(context:AccountContext,title:String?,text:String,actions:[TextAlertAction])->ViewController{ViewController()}
final class EndpointRequest {
 var next:((Any)->Void)?;var completed:(()->Void)?;var failed:((Int)->Void)?;var disposed=false
 func start(next:@escaping(Any)->Void,error:@escaping(Int)->Void,completed:@escaping()->Void)->Disposable?{
  self.next=next;self.completed=completed;self.failed=error;return ActionDisposable{self.disposed=true}
 }
}
enum NagramiXDNSResolver {
 static var requests:[EndpointRequest]=[]
 static func testEndpoint(_ url:String,hostname:String)->EndpointRequest{let r=EndpointRequest();requests.append(r);return r}
}
'''

ALERT_STORAGE = r'''
 var content:[AnyComponentWithIdentity<AlertComponentEnvironment>]=[]
 var actions:[Action]=[];var enabled:[AnyHashable:Bool]=[:]
 var dismissed:((Bool)->Void)?;var dismissals=0;var actionUpdates=0
 private let subscriptions=DisposableSet()
 private var wired:Set<AnyHashable>=[]
'''
ALERT_INIT = r'''
 super.init()
 subscriptions.add(contentSignal.start(next:{[weak self] in self?.content=$0}))
 subscriptions.add(actionsSignal.start(next:{[weak self] actions in
  guard let self else{return};self.actions=actions;self.actionUpdates+=1
  for action in actions where self.wired.insert(action.id).inserted {
   self.subscriptions.add(action.isEnabled.start(next:{[weak self] in self?.enabled[action.id]=$0}))
  }
 }))
 // Native AlertScreen mounts content before laying out actions. Mounting the
 // input publishes its initial value through the actual ExternalState promise.
 input.mount()
'''
ALERT_METHODS = r'''
 deinit{subscriptions.dispose()}
 func dismiss(){dismissals+=1;dismissed?(true);subscriptions.dispose()}
 var input:AlertInputFieldComponent{content[2].component.value as! AlertInputFieldComponent}
 var hint:String{switch (content[1].component.value as! AlertTextComponent).content{case let .plain(value):return value}}
 var saveEnabled:Bool{enabled[actions[1].id] ?? false}
'''
INPUT_BOUNDARY = r'''
 enum Keyboard{case URL};enum Capitalization{case none};enum Correction{case no}
 let state:ExternalState;let initial:String;let returnKeyAction:()->Void;let hasClearButton:Bool
 var errors=0
 init(context:AccountContext,initialValue:String,placeholder:String,characterLimit:Int,hasClearButton:Bool,keyboardType:Keyboard,autocapitalizationType:Capitalization,autocorrectionType:Correction,isInitiallyFocused:Bool,externalState:ExternalState,shouldChangeText:(String)->Bool,returnKeyAction:@escaping()->Void){
  state=externalState;initial=initialValue;self.returnKeyAction=returnKeyAction;self.hasClearButton=hasClearButton
  state.animateError={[weak self] in self?.errors+=1}
 }
 func mount(){setText(initial)}
 func setText(_ text:String){state.value=text;state.valuePromise.set(text)}
'''

TESTS = r'''
@main struct DohTests {static func main(){
 var saved:[String]=[];var removed=0
 func editor(_ value:String="")->AlertScreen{
  nagramiXCustomDohController(context:AccountContext(),initialValue:value,apply:{saved.append($0)},clear:{removed+=1}) as! AlertScreen
 }
 let c=editor()
 check(c.actions.map{$0.title}==["Отменить","Сохранить"],"empty field displays Cancel and Save")
 check(c.actions[0].type == .generic && !c.saveEnabled,"empty Cancel is neutral and Save disabled")
 check(c.hint=="Введите корректный HTTPS URL\nс именем сервера без пробелов.","preposition starts new hint line")
 check(c.content.map{$0.id}==["title","text","input"] && c.input.hasClearButton,"native title body input and clear control preserved")
 let ids=c.actions.map{$0.id};let field=c.input
 for text in ["h","https://"," ","https://dns.example.org/dns-query"] {
  c.input.setText(text)
  check(c.actions[0].title=="Удалить" && c.actions[0].type == .destructive,"any nonempty field displays Delete")
  check(c.actions.map{$0.id}==ids && c.input === field,"typing keeps button identities and input instance")
  check(c.saveEnabled==(validatedNagramiXDohUrl(text) != nil),"Save follows current HTTPS validity")
 }
 let staleDelete=c.actions[0].action
 c.input.setText("")
 check(c.actions[0].title=="Отменить" && c.actions[0].type == .generic && !c.saveEnabled,"clear returns Cancel and disables Save")
 staleDelete();c.actions[0].action()
 check(removed==0 && saved.isEmpty && c.dismissals==1,"Cancel preserves saved DNS even through stale Delete closure")
 let existing=editor("https://dns.example.org/dns-query")
 check(existing.actions[0].title=="Удалить" && existing.saveEnabled,"saved endpoint opens with Delete and enabled Save")
 existing.input.setText("");existing.actions[0].action()
 check(removed==0 && existing.dismissals==1,"clearing saved input then Cancel preserves saved DNS")
 let deleting=editor();deleting.input.setText("x");deleting.actions[0].action();deleting.actions[0].action()
 check(removed==1 && deleting.dismissals==1,"Delete uses existing removal callback once")
 let invalid=editor("http://dns.example.org");let count=NagramiXDNSResolver.requests.count
 invalid.input.returnKeyAction()
 check(!invalid.saveEnabled && invalid.input.errors==1 && NagramiXDNSResolver.requests.count==count,"invalid Return never starts endpoint request")
 let saving=editor("https://dns.example.org/dns-query");saving.actions[1].action();saving.input.returnKeyAction()
 check(NagramiXDNSResolver.requests.count==count+1,"Save and Return share one submission")
 let request=NagramiXDNSResolver.requests.last!;request.next?("93.184.216.34");request.completed?()
 check(saved==["https://dns.example.org/dns-query"] && saving.dismissals==1,"successful endpoint test saves once")
 let pending=editor("https://dns.example.org/dns-query");pending.actions[1].action();let late=NagramiXDNSResolver.requests.last!
 pending.input.setText("");pending.actions[0].action();late.next?("93.184.216.34");late.completed?()
 check(late.disposed && saved.count==1 && removed==1 && pending.dismissals==1 && pending.presented==0,"Cancel during validation rejects late response without deleting DNS")
 let retry=editor("https://dns.example.org/dns-query");retry.actions[1].action();NagramiXDNSResolver.requests.last!.failed?(1)
 check(retry.presented==1 && retry.dismissals==0 && retry.input.errors==1,"failed endpoint stays editable")
 let attempts=NagramiXDNSResolver.requests.count;retry.actions[1].action()
 check(NagramiXDNSResolver.requests.count==attempts+1,"failed endpoint permits explicit retry")
 NagramiXDNSResolver.requests.last!.next?("93.184.216.34")
 check(saved.count==2 && retry.dismissals==1,"retry still saves once")
 let outside=editor("https://dns.example.org");outside.actions[1].action();let delayed=NagramiXDNSResolver.requests.last!;outside.dismiss();delayed.next?("93.184.216.34")
 check(delayed.disposed && saved.count==2 && removed==1,"outside dismissal cannot apply delayed validation")
 for text in ["", " https://dns.example.org", "https://dns.example.org ", "http://dns.example.org", "https://u:p@dns.example.org", "https://dns.exam ple.org"] {
  check(validatedNagramiXDohUrl(text)==nil,"HTTPS URL validation unchanged")
 }
 print("PASS DoH empty action production checks: \(checks)")
}}
'''
