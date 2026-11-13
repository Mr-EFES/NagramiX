"""Actual master gates, message readiness, UI observers and context cancellation.

Native UI/engine I/O is an explicit boundary. No RPC or recognition is run.
"""
from validate_quick_format import block
from original_video_mode_runtime import signal_library
RUNTIME='submodules/NagramiXTranscription/Sources/Runtime.swift'
BASE='submodules/TelegramUI/Components/Chat/'
COMMON=BASE+'ChatMessageItemCommon/Sources/ChatMessageItemCommon.swift'
FILE=BASE+'ChatMessageInteractiveFileNode/Sources/ChatMessageInteractiveFileNode.swift'
ROUND=BASE+'ChatMessageInteractiveInstantVideoNode/Sources/ChatMessageInteractiveInstantVideoNode.swift'


def fixture(source):
    runtime=(source/RUNTIME).read_text();file=(source/FILE).read_text();round=(source/ROUND).read_text()
    code=signal_library(source)+BOUNDARY
    code+='\n'+block((source/COMMON).read_text(),'public enum TranscribedText:').replace('public ','')
    code+='\n'+block(file,'private func nagramiXReadyForcedTranscript(').replace('private ','',1)
    code+='\nenum NagramiXTranscriptionRuntime {\n'
    for marker in ['    public static var requestsEnabled:', '    public static func hasReadyTranscript(', '    public static func hasTemporaryTranscript(', '    private static let lifecycleObservers:']:
        code+='\n'+block(runtime,marker).replace('public ','')
    code+='''
    private static var contextJobs:[String:MetaDisposable]=[:]
    static func testInstallContext(_ job:MetaDisposable){_ = lifecycleObservers;contextJobs["context"]=job}
    static var testContextCount:Int{contextJobs.count}
}
'''
    for name,full in [('FileProbe',file),('RoundProbe',round)]:
        method=block(full,'    private func transcribe()')
        # Unchanged start of real tap handler through cached temporary toggle.
        prefix=method[:method.index('        let temporary =')]
        prefix=prefix.replace('private func transcribe()','func transcribe()')
        observer=block(full,'        self.nagramiXTranscriptionSettingsObserver = NotificationCenter.default.addObserver(')
        prefix += '\n_ = arguments\n' if name=='FileProbe' else ''
        code+='\nfinal class '+name+': ProbeBase {\noverride init(){super.init();\n'+observer+'\n}\n'+prefix+'\n terminalRequests += 1\n}\n}\n'
    for name,full,indent in [('fileButton',file,'                '),('roundButton',round,'                    ')]:
        gate=block(full,indent+'if !NagramiXTranscriptionRuntime.requestsEnabled {')
        code+='\nfunc '+name+'(_ eligible:Bool,_ message:Message,_ forced:TranscribedText?=nil)->Bool {\nvar displayTranscribe=eligible\n'
        if name=='fileButton':code+='let arguments=ProbeArguments(message:message)\nlet forcedAudioTranscriptionText=forced\n'
        else:code+='let item=ProbeItem(message:message)\n_ = forced\n'
        code+=gate+'\nreturn displayTranscribe\n}\n'
    code+='\n'+CHECKS
    return code


BOUNDARY=r'''
enum EngineMessage {typealias Id=Int}
typealias EngineRawMessage=Message
class AudioTranscriptionMessageAttribute {
 enum TranscriptionError {case generic}
 var text:String;var isPending:Bool;var error:TranscriptionError?
 init(_ text:String,pending:Bool=false,error:TranscriptionError?=nil){self.text=text;self.isPending=pending;self.error=error}
}
struct MessageId {var namespace:Int=0}
struct Message {var id=MessageId();var attributes:[Any]=[];var temporary=false}
enum Namespaces {enum Message {static let Cloud=0}}
func nagramiXCanTranscribeTemporaryMedia(_ message:Message)->Bool{message.temporary}
struct TranscriptionConfiguration {var enabled=true}
enum NagramiXTranscriptionSettings {static var current=TranscriptionConfiguration();static let changed=Notification.Name("NagramiXTranscriptionSettingsChanged")}
enum UIApplication {static let didEnterBackgroundNotification=Notification.Name("background");static let didReceiveMemoryWarningNotification=Notification.Name("memory")}
final class NagramiXTranscriptionCoordinator {
 static let shared=NagramiXTranscriptionCoordinator();var cancellations=0
 func cancelAll(){cancellations += 1}
}
struct AccountContext {}
struct ProbeArguments {var message:Message}
struct ProbeItem {var message:Message;var context=AccountContext()}
enum AudioTranscriptionState {case collapsed,expanded,inProgress}
class ProbeBase {
 var arguments:Int?=1;var context:AccountContext?=AccountContext();var message:Message?;var item:ProbeItem?
 var forcedAudioTranscriptionText:TranscribedText?
 var nagramiXTranscriptionSettingsObserver:NSObjectProtocol?
 let nagramiXTranscriptionDisposable=MetaDisposable();var nagramiXTranscribingId:Int?
 var isWaitingForCollapse=false;var beforeNativeRequest:(()->Void)?
 var transcribeDisposable:Disposable?;var audioTranscriptionState:AudioTranscriptionState = .collapsed
 var layouts=0;var expansionNotifications=0;var terminalRequests=0
 var updateTranscriptionExpanded:((AudioTranscriptionState)->Void)?
 init(){updateTranscriptionExpanded={ [weak self] _ in self?.expansionNotifications += 1 }}
 func requestUpdateLayout(_ animated:Bool){layouts += 1}
 func setMessage(_ message:Message){self.message=message;self.item=ProbeItem(message:message)}
 deinit{if let observer=nagramiXTranscriptionSettingsObserver{NotificationCenter.default.removeObserver(observer)}}
}
'''

CHECKS=r'''
@main struct Main {
 static func main() {
  var checks=0
  func check(_ ok:Bool,_ why:String){guard ok else{print("FAIL "+why);exit(91)};checks+=1}
  for pending in [false,true] {for errored in [false,true] {for text in ["","text"] {
   let attr=AudioTranscriptionMessageAttribute(text,pending:pending,error:errored ? .generic:nil)
   let message=Message(attributes:[attr])
   check(NagramiXTranscriptionRuntime.hasReadyTranscript(message)==(!pending && !errored && !text.isEmpty),"ready transcript requires actual completed text")
  }}}
  check(!NagramiXTranscriptionRuntime.hasReadyTranscript(Message()),"missing transcript is not cached success")
  check(nagramiXReadyForcedTranscript(.success(text:"ready",isPending:false)),"native forced text remains readable")
  check(!nagramiXReadyForcedTranscript(.success(text:"partial",isPending:true)),"partial forced text is not ready")
  check(!nagramiXReadyForcedTranscript(.error(.generic)),"error is not a ready transcript")
  check(!nagramiXReadyForcedTranscript(nil),"nil forced transcript is not ready")
  for enabled in [false,true] {for temporary in [false,true] {
   NagramiXTranscriptionSettings.current.enabled=enabled
   let f=FileProbe();let v=RoundProbe();let message=Message(temporary:temporary)
   f.setMessage(message);v.setMessage(message)
   f.transcribe();v.transcribe()
   check(f.terminalRequests==(enabled ? 1:0),"file tap blocks all new requests when master OFF")
   check(v.terminalRequests==(enabled ? 1:0),"round tap blocks all new requests when master OFF")
  }}
  for enabled in [false,true] {for eligible in [false,true] {for cached in [false,true] {
   NagramiXTranscriptionSettings.current.enabled=enabled
   let m=Message(attributes:cached ? [AudioTranscriptionMessageAttribute("ready")]:[])
   check(fileButton(eligible,m)==(eligible && (enabled || cached)),"file button master governs native Premium/trial/boost eligibility")
   check(roundButton(eligible,m)==(eligible && (enabled || cached)),"round button master governs native Premium/trial/boost eligibility")
   check(fileButton(eligible,Message(),.success(text:"ready",isPending:false))==eligible,"completed native forced text remains available with OFF")
  }}}
  NagramiXTranscriptionSettings.current.enabled=false
  let ready=AudioTranscriptionMessageAttribute("kept")
  for make in [ {FileProbe() as ProbeBase}, {RoundProbe() as ProbeBase} ] {
   let node=make();node.setMessage(Message(attributes:[ready],temporary:true))
   if let file=node as? FileProbe {file.transcribe()}else{(node as! RoundProbe).transcribe()}
   check(node.audioTranscriptionState == .expanded && node.terminalRequests==0,"OFF opens cached temporary text without request")
   if let file=node as? FileProbe {file.transcribe()}else{(node as! RoundProbe).transcribe()}
   check(node.audioTranscriptionState == .collapsed,"cached text still collapses")
  }
  let f=FileProbe();let v=RoundProbe();f.setMessage(Message(attributes:[ready]));v.setMessage(Message(attributes:[ready]))
  var nativeCancelled=0;var localCancelled=0;var contextCancelled=0
  for node in [f as ProbeBase,v as ProbeBase] {
   node.transcribeDisposable=ActionDisposable{nativeCancelled += 1}
   node.nagramiXTranscriptionDisposable.set(ActionDisposable{localCancelled += 1})
   node.nagramiXTranscribingId=7;node.audioTranscriptionState = .inProgress
  }
  let job=MetaDisposable();job.set(ActionDisposable{contextCancelled += 1});NagramiXTranscriptionRuntime.testInstallContext(job)
  NotificationCenter.default.post(name:NagramiXTranscriptionSettings.changed,object:nil)
  check(nativeCancelled==2 && localCancelled==2,"OFF disposes native and local UI operations")
  check(contextCancelled==1 && NagramiXTranscriptionRuntime.testContextCount==0,"OFF clears outliving context operation")
  withExtendedLifetime(job) {}
  check(f.nagramiXTranscribingId==nil && v.nagramiXTranscribingId==nil,"old operation identities cleared")
  check(f.audioTranscriptionState == .collapsed && v.audioTranscriptionState == .collapsed,"OFF clears in-progress UI")
  check(f.layouts==1 && v.layouts==1,"open rows refresh immediately")
  check(ready.text=="kept" && NagramiXTranscriptionRuntime.hasReadyTranscript(f.message!),"disabling never erases completed text")
  NagramiXTranscriptionSettings.current.enabled=true
  NotificationCenter.default.post(name:NagramiXTranscriptionSettings.changed,object:nil)
  check(f.layouts==2 && v.layouts==2,"re-enable refreshes both row types")
  print("Transcription master production checks: \(checks)")
 }
}
'''
