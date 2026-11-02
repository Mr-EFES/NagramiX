import Foundation
private var checks=0
private func check(_ value:@autoclosure()->Bool,_ label:String){checks+=1;if !value(){fatalError(label)}}
@main struct AnalyzerTests {
 static func main()async{
  let available:([Locale],[Locale]) = await withCheckedContinuation { continuation in
   NagramiXTranscriptionAnalyzer.locales { supported, installed in continuation.resume(returning:(supported,installed)) }
  }
  check(available.0.count == 2 && available.1.count == 1,"Real supported and installed locales are listed separately")
  let url=URL(fileURLWithPath:"/tmp/test-audio.m4a")
  func run(language:String="en-US",token:NagramiXTranscriptionCancellation=NagramiXTranscriptionCancellation())async->Result<String,NagramiXTranscriptionFailure>{
   await withCheckedContinuation{continuation in NagramiXTranscriptionAnalyzer.transcribe(url:url,language:language,automatic:false,cancellation:token){continuation.resume(returning:$0)}}
  }
  if case .success("Дословная речь")=await run(){}else{fatalError("Final transcript")};check(NagramiXTranscriptionApple.legacyCalls==0,"Installed model uses analyzer")
  if case .failure(.unavailable)=await run(language:"ru-RU"){}else{fatalError("Legacy fallback")};check(NagramiXTranscriptionApple.legacyCalls==1,"No implicit asset download")
  check(AssetInstallationRequest.installs==0,"No download during recognition")
  let installed:Result<String,NagramiXTranscriptionFailure>=await withCheckedContinuation{continuation in NagramiXTranscriptionAnalyzer.install(language:"ru-RU"){continuation.resume(returning:$0)}}
  if case .success=installed{}else{fatalError("Explicit model install")};check(AssetInstallationRequest.installs==1,"One explicit installation")
  let unsupported:Result<String,NagramiXTranscriptionFailure>=await withCheckedContinuation{continuation in NagramiXTranscriptionAnalyzer.install(language:"auto"){continuation.resume(returning:$0)}}
  if case .failure(.unavailable)=unsupported{}else{fatalError("No invented auto locale")};check(AssetInstallationRequest.installs==1,"No unsupported download")
  SpeechAnalyzer.stall=true
  let token=NagramiXTranscriptionCancellation()
  let task=Task{await run(token:token)}
  try? await Task.sleep(nanoseconds:100_000_000);token.cancel()
  if case .failure(.cancelled)=await task.value{}else{fatalError("Cancel result")}
  check(SpeechAnalyzer.cancels>0,"Cancel reaches active analyzer")
  print("PASS: \(checks) production SpeechAnalyzer task / asset / cancellation checks at Apple boundary")
 }
}
