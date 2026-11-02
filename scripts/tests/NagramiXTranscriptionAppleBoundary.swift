import Foundation
// Speech.framework boundary only. The real wrapper is compiled with warnings as errors.
enum SFSpeechRecognizerAuthorizationStatus { case notDetermined,denied,authorized }
final class SFSpeechRecognitionTask { static var cancels=0;func cancel(){Self.cancels+=1} }
final class SFSpeechURLRecognitionRequest {
 enum Hint { case dictation }
 var requiresOnDeviceRecognition=false;var shouldReportPartialResults=true;var taskHint:Hint = .dictation
 init(url:URL){}
}
struct SFSpeechRecognitionResult { let isFinal:Bool;let bestTranscription:SFTranscription }
struct SFTranscription { let formattedString:String }
final class SFSpeechRecognizer {
 static var status:SFSpeechRecognizerAuthorizationStatus = .authorized
 static var local=true;static var stall=false;static var authorizations=0;static var requests=0;static var lastRequest:SFSpeechURLRecognitionRequest?
 var supportsOnDeviceRecognition:Bool{Self.local};let isAvailable=true
 init?(locale:Locale){}
 static func authorizationStatus()->SFSpeechRecognizerAuthorizationStatus{status}
 static func requestAuthorization(_ completion:@escaping(SFSpeechRecognizerAuthorizationStatus)->Void){authorizations+=1;status = .authorized;completion(status)}
 func recognitionTask(with request:SFSpeechURLRecognitionRequest,resultHandler:@escaping(SFSpeechRecognitionResult?,Error?)->Void)->SFSpeechRecognitionTask {
  Self.requests+=1;Self.lastRequest=request
  if !Self.stall {DispatchQueue.main.async{resultHandler(.init(isFinal:true,bestTranscription:.init(formattedString:" Дословно ")),nil)}}
  return .init()
 }
}
