"""Контроллер DoH, настоящий ComponentView._update и синхронный SwiftSignalKit.

UIKit/rendering/context storage — явная граница. Методы обновления/очистки,
публикация ExternalState и callbacks Alert берутся из guarded native source.
"""
from pathlib import Path
from validate_quick_format import block
import doh_empty_action_runtime as old

EDITOR, INPUT, ALERT, SK = old.EDITOR, old.INPUT, old.ALERT, old.SK
HOST = 'submodules/ComponentFlow/Source/Host/ComponentHostView.swift'
STATE = 'submodules/ComponentFlow/Source/Base/Component.swift'
ACTION = 'submodules/TelegramUI/Components/AlertComponent/Sources/AlertActionComponent.swift'


def fixture(source):
    code = old.fixture(source)
    combine = (source / (SK + 'Signal_Combine.swift')).read_text()
    native_combine = '\n'.join(block(combine, marker) for marker in [
        'private struct SignalCombineState {', 'private func combineLatestAny<', 'private func signalOfAny<',
        'public func combineLatest<T1, T2, E>(queue: Queue? = nil, _ s1: Signal<T1, E>, _ s2: Signal<T2, E>)'])
    state = (source / STATE).read_text()
    host = (source / HOST).read_text().split('public final class ComponentView<', 1)[1]
    update = block(host, '    private func _update(')
    # Only the view/context/erasure type names differ in this portable boundary.
    update = update.replace('AnyComponent<', 'NativeComponent<').replace('UIView', 'NativeView')
    native_state = block(state, 'open class ComponentState {') + '\n' + block(state, 'public final class EmptyComponentState:')
    native_input = (source / INPUT).read_text()
    set_text = block(native_input, '        public func setText(text:')
    typed_text = block(native_input, '        @objc private func textDidChange()').replace('@objc ', '')
    publication = '            component.externalState.value = self.currentText\n            component.externalState.valuePromise.set(self.currentText)'
    assert native_input.count(publication) == 1
    clear = block(native_input, '                        action: { [weak self] in')
    clear = clear.split('action: ', 1)[1]
    # Keep the production native queue's synchronous fast path. Replacing it
    # with an always-async fake would conceal build219's actual crash.
    code = code.replace(old.BOUNDARY_PREFIX, native_combine + '\n' + NATIVE_PREFIX + native_state + '\n' + NATIVE_HOST.replace('__UPDATE__', update) + '\n' + old.BOUNDARY_PREFIX, 1)
    storage = old.ALERT_STORAGE + ALERT_STORAGE
    code = code.replace(old.ALERT_STORAGE, storage, 1)
    alert = (source / ALERT).read_text()
    callback = block(alert, ').start(next: { [weak self] content, actions in').split('next: ', 1)[1]
    init = ALERT_INIT.replace('__CALLBACK__', callback)
    code = code.replace(old.ALERT_INIT, init, 1)
    code = code.replace(' var saveEnabled:Bool{enabled[actions[1].id] ?? false}', ' var saveEnabled:Bool{saveView.isEnabled}', 1)
    code = code.replace('func dismiss(){dismissals+=1;dismissed?(true);subscriptions.dispose()}', 'func dismiss(){dismissals+=1;dismissed?(true);subscriptions.dispose();saveView.dispose()}', 1)
    code = code.replace(old.INPUT_BOUNDARY, INPUT_BOUNDARY.replace('__SET_TEXT__', set_text).replace('__TYPED_TEXT__', typed_text).replace('__PUBLICATION__', publication).replace('__CLEAR__', clear), 1)
    action = (source / ACTION).read_text()
    enabled = block(action, '|> deliverOnMainQueue).start(next: { [weak self] isEnabled in').split('next: ', 1)[1]
    code = code.replace(old.BOUNDARY_PREFIX, SAVE_BOUNDARY.replace('__CALLBACK__', enabled) + '\n' + old.BOUNDARY_PREFIX, 1)
    # Replay all existing Save/Delete/Cancel/endpoint/late callback assertions.
    tests = old.TESTS.replace('  nagramiXCustomDohController(context:', '  let result = nagramiXCustomDohController(context:', 1)
    tests = tests.replace('clear:{removed+=1}) as! AlertScreen\n }', 'clear:{removed+=1}) as! AlertScreen\n  drainQueue();return result\n }', 1)
    tests = tests.replace(' let c=editor()', EXTRA_TESTS + '\n let c=editor()', 1)
    code = code.replace(old.TESTS, tests, 1)
    return code


NATIVE_PREFIX = r'''
#if canImport(CoreGraphics)
import CoreGraphics
#endif
public enum ComponentTransition {case immediate;static func easeInOut(duration:Double)->Self{.immediate}}
class EnvironmentStorage {var _isUpdated=false;func calculateIsUpdated()->Bool{_isUpdated}}
final class Environment<E>:EnvironmentStorage {}
enum EnvironmentBuilder {static var _environment:EnvironmentStorage?}
final class NativeContext {
 let erasedState=EmptyComponentState();var erasedEnvironment:EnvironmentStorage=Environment<Int>()
}
class NativeView {
 let nativeContext=NativeContext()
 func context<E>(component:NativeComponent<E>)->NativeContext{nativeContext}
}
struct NativeComponent<E>:Equatable {
 let id:Int;let make:()->NativeView;let render:(NativeView)->Void
 func _makeView()->NativeView{make()}
 func _update(view:NativeView,availableSize:CGSize,environment:Any,transition:ComponentTransition)->CGSize{render(view);return availableSize}
 static func ==(a:Self,b:Self)->Bool{a.id==b.id}
}
'''

NATIVE_HOST = r'''
final class NativeComponentView<E> {
 typealias EnvironmentType=E
 private var currentComponent:NativeComponent<E>?
 private var currentContainerSize:CGSize?
 private var currentSize:CGSize?
 private(set) var view:NativeView?
 private(set) var isUpdating=false
 weak var parentState:ComponentState?
 func render(_ component:NativeComponent<E>,force:Bool=false){
  currentSize=_update(transition:.immediate,component:component,maybeEnvironment:{Environment<E>()},updateEnvironment:true,forceUpdate:force,containerSize:CGSize(width:240,height:65))
 }
 __UPDATE__
}
private func drainQueue(){
 for _ in 0..<4 {
  var finished=false
  DispatchQueue.main.async{finished=true}
  let deadline=Date().addingTimeInterval(2)
  while !finished && Date()<deadline {_ = RunLoop.main.run(mode:.default,before:Date().addingTimeInterval(0.002))}
  precondition(finished,"main queue did not drain")
 }
}
'''

ALERT_STORAGE = r'''
 private let root=NativeComponentView<Int>()
 private let saveView=NativeSaveAction()
 private var state:ComponentState?
 private var isUpdating=false
 private func render(){
  root.render(NativeComponent(id:0,make:{NativeView()},render:{[weak self] view in
   guard let self else{return};self.isUpdating=true;defer{self.isUpdating=false}
   self.state=view.nativeContext.erasedState
   self.input.mount(parent:self.state!)
   if let save=self.actions.last {self.saveView.mount(save,parent:self.state!)}
  }),force:true)
 }
'''

ALERT_INIT = r'''
 super.init()
 subscriptions.add((combineLatest(queue:Queue.mainQueue(),contentSignal,actionsSignal) |> deliverOnMainQueue).start(next:__CALLBACK__))
 // The real AlertScreen callback updates its state. Mount the recording root
 // after the first content/actions pair; subsequent pairs use that native state.
 subscriptions.add(actionsSignal.start(next:{[weak self] _ in
  guard let self else{return};self.actionUpdates+=1
  if self.state == nil && !self.content.isEmpty {self.render()}
 }))
'''

SAVE_BOUNDARY = r'''
final class NativeSaveAction {
 private var subscription:Disposable?
 private var isUpdating=false
 private var state:ComponentState?
 private(set) var isEnabled=true
 func mount(_ action:AlertScreen.Action,parent:ComponentState){
  state=parent
  if subscription == nil {
   isUpdating=true
   subscription=(action.isEnabled |> deliverOnMainQueue).start(next:__CALLBACK__)
   isUpdating=false
  }
 }
 func dispose(){subscription?.dispose()}
 deinit{dispose()}
}
'''

INPUT_BOUNDARY = r'''
 enum Keyboard{case URL};enum Capitalization{case none};enum Correction{case no}
 let state:ExternalState;let initial:String;let returnKeyAction:()->Void;let hasClearButton:Bool
 var externalState:ExternalState{state}
 var errors=0
 private let item=NativeComponentView<Int>()
 private var nativeView:InputView?
 final class InputView:NativeView {
  final class TextField {var text:String?}
  let textField=TextField();var isUpdating=false;var state:ComponentState?
  var currentText:String{textField.text ?? ""}
  __SET_TEXT__
  __TYPED_TEXT__
  func typeText(_ text:String){textField.text=text;self.textDidChange()}
  var clearAction:()->Void{__CLEAR__}
 }
 init(context:AccountContext,initialValue:String,placeholder:String,characterLimit:Int,hasClearButton:Bool,keyboardType:Keyboard,autocapitalizationType:Capitalization,autocorrectionType:Correction,isInitiallyFocused:Bool,externalState:ExternalState,shouldChangeText:(String)->Bool,returnKeyAction:@escaping()->Void){
  state=externalState;initial=initialValue;self.returnKeyAction=returnKeyAction;self.hasClearButton=hasClearButton
  state.animateError={[weak self] in self?.errors+=1}
 }
 func mount(parent:ComponentState){
  item.parentState=parent
  item.render(NativeComponent(id:0,make:{InputView()},render:{[weak self] v in
   guard let self else{return};let view=v as! InputView
   let first=self.nativeView == nil;self.nativeView=view
   view.isUpdating=true;defer{view.isUpdating=false}
   view.state=view.nativeContext.erasedState
   if first{view.textField.text=self.initial}
   let component=self
   __PUBLICATION__
  }))
 }
 private var currentText:String{nativeView!.currentText}
 var isMounted:Bool{nativeView != nil}
 func setText(_ text:String){nativeView!.typeText(text);drainQueue()}
 func pressClear(){nativeView!.clearAction();drainQueue()}
 func queueClearThenCancel(_ action:()->Void){nativeView!.clearAction();action();drainQueue()}
'''

EXTRA_TESTS = r'''
 // Real native clear closure -> setText -> local ComponentView update ->
 // ExternalState publication -> Alert actions/root update. Old219 reenters
 // the same ComponentView and hits its unchanged native precondition.
 let clearable=editor("https://dns.example.org/dns-query")
 let originalInput=clearable.input
 for _ in 0..<12 {
  clearable.input.pressClear()
  check(clearable.input === originalInput && clearable.input.state.value.isEmpty,"native X clears the same input")
  check(clearable.actions[0].title=="Отменить" && !clearable.saveEnabled,"native X returns Cancel and disables Save")
  check(clearable.dismissals==0 && removed==0 && saved.isEmpty,"native X never deletes or saves DNS or closes editor")
  clearable.input.setText("https://dns.example.org/dns-query")
  check(clearable.saveEnabled && clearable.actions[0].title=="Удалить","typing after X restores Delete and Save")
 }
 let closing=editor("https://dns.example.org/dns-query")
 closing.input.queueClearThenCancel(closing.actions[0].action)
 check(closing.dismissals==1 && removed==0,"Cancel before queued UI notification still reads empty field")
 let pendingBefore=closing.actionUpdates
 drainQueue()
 check(closing.actionUpdates==pendingBefore,"disposed actions reject pending delivery after dismissal")
'''
