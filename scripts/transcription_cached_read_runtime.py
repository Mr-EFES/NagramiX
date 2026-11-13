"""Run actual tap prefixes with actual native retry decisions and explicit RPC boundary."""
from validate_quick_format import block
import feature_transcription_master_runtime as master


def fixture(source):
    code=master.fixture(source)
    code=code.replace('enum EngineMessage {typealias Id=Int}', 'struct EngineMessage {typealias Id=Int;var attributes:[Any];init(_ message:Message){attributes=message.attributes}}')
    common=(source/master.COMMON).read_text()
    code+='\n'+block(common,'public func transcribedText(message:').replace('public ','')
    for name,path in [('FileProbe',master.FILE),('RoundProbe',master.ROUND)]:
        source_method=block((source/path).read_text(),'    private func transcribe()')
        decision=source_method[source_method.index('        var shouldBeginTranscription = false'):source_method.index('        if shouldBeginTranscription {')]
        gate='            guard NagramiXTranscriptionRuntime.requestsEnabled else { return }\n'
        if gate not in source_method:gate=''
        native_tail=decision+'\nself.beforeNativeRequest?()\nif shouldBeginTranscription {\n'+gate+' terminalRequests += 1\n}\n_ = shouldExpandNow\n'
        old_class=block(code,'final class '+name+':')
        assert old_class.count(' terminalRequests += 1')==1
        code=code.replace(old_class,old_class.replace(' terminalRequests += 1',native_tail,1),1)
    mark='  print("Transcription master production checks: \\(checks)")'
    assert mark in code
    code=code.replace(mark,CHECKS+mark,1)
    return code


CHECKS=r'''
  NagramiXTranscriptionSettings.current.enabled=false
  let forced=FileProbe();forced.setMessage(Message());forced.forcedAudioTranscriptionText = .success(text:"local result",isPending:false)
  forced.transcribe()
  check(forced.terminalRequests==0 && forced.audioTranscriptionState == .expanded,"OFF reads forced cache without native retry")
  forced.transcribe()
  check(forced.terminalRequests==0 && forced.audioTranscriptionState == .collapsed && forced.isWaitingForCollapse,"OFF collapses forced cache without native retry")
  for create in [{FileProbe() as ProbeBase},{RoundProbe() as ProbeBase}] {
   for state in [AudioTranscriptionState.collapsed,.expanded,.inProgress] {
    let node=create();node.audioTranscriptionState=state;node.setMessage(Message(attributes:[ready]));node.isWaitingForCollapse=true
    if let file=node as? FileProbe{file.transcribe()}else{(node as! RoundProbe).transcribe()}
    check(node.terminalRequests==0,"ordinary completed cache never creates native request")
    check(node.audioTranscriptionState == (state == .expanded ? .collapsed:.expanded),"OFF opens ordinary ready text directly")
    check(node.isWaitingForCollapse == (state == .expanded),"cached open resets waiting-for-collapse state")
   }
   let malformed=create();malformed.setMessage(Message(attributes:[AudioTranscriptionMessageAttribute("partial",pending:true),ready]))
   if let file=malformed as? FileProbe{file.transcribe()}else{(malformed as! RoundProbe).transcribe()}
   check(malformed.terminalRequests==0,"pending-first mixed attributes cannot bypass OFF via later ready text")
   NagramiXTranscriptionSettings.current.enabled=true
   let changing=create();changing.setMessage(Message());changing.beforeNativeRequest={NagramiXTranscriptionSettings.current.enabled=false}
   if let file=changing as? FileProbe{file.transcribe()}else{(changing as! RoundProbe).transcribe()}
   check(changing.terminalRequests==0,"final native gate rechecks a changed master before request")
  }
'''
