import Foundation
private var checks=0
private func check(_ value: @autoclosure () -> Bool,_ label:String) { checks += 1;if !value() { fatalError(label) } }
@main struct TranscriptionKeychainTests {
    static func main() {
        let service=(Bundle.main.bundleIdentifier ?? "NagramiX")+".transcription.keys"
        let translation=(Bundle.main.bundleIdentifier ?? "NagramiX")+".translation.keys"
        for provider in [NagramiXTranscriptionProvider.apple,.whisper,.telegram] { check(!NagramiXTranscriptionKeys.save("wrong",provider:provider),"No local/server key");check(NagramiXTranscriptionKeys.read(provider)==nil,"No unrelated key read") }
        KeychainBoundary.items[translation+":gemini"]=Data("{\"key\":\"translation-own\"}".utf8)
        check(NagramiXTranscriptionKeys.read(.gemini)==nil,"No implicit translation key reuse")
        check(NagramiXTranscriptionKeys.importTranslationKey(.gemini)=="translation-own","Explicit key import")
        check(NagramiXTranscriptionKeys.importTranslationKey(.groq)==nil,"No wrong provider import")
        for provider in [NagramiXTranscriptionProvider.groq,.gemini,.chatgpt] {
            let prior=NagramiXTranscriptionSettings.current.credentialRevision
            check(NagramiXTranscriptionKeys.save("own-"+provider.rawValue,provider:provider),"Save own key")
            check(NagramiXTranscriptionSettings.current.credentialRevision != prior,"Credentials invalidate pending writes and cache")
            check(NagramiXTranscriptionKeys.read(provider)=="own-"+provider.rawValue,"Read exact provider key")
            check(KeychainBoundary.lastQuery[kSecAttrService] as? String==service,"Separate ASR service")
            check(KeychainBoundary.lastQuery[kSecAttrSynchronizable] as? Bool==false,"No iCloud synchronization")
            check(NagramiXTranscriptionKeys.save("updated",provider:provider),"Update key")
            check(NagramiXTranscriptionKeys.read(provider)=="updated","Read updated key")
            let beforeDenied=NagramiXTranscriptionSettings.current.credentialRevision
            KeychainBoundary.denied=true
            check(!NagramiXTranscriptionKeys.save("denied",provider:provider),"Handle OS denial")
            check(NagramiXTranscriptionSettings.current.credentialRevision==beforeDenied,"No false saved revision")
            KeychainBoundary.denied=false
            check(!NagramiXTranscriptionKeys.save("header\r\ninjection",provider:provider),"Reject control chars")
            check(NagramiXTranscriptionKeys.save(nil,provider:provider),"Delete key")
            check(NagramiXTranscriptionKeys.read(provider)==nil,"Deleted")
        }
        check(KeychainBoundary.items[translation+":gemini"] != nil,"Preserve translation credential")
        print("PASS: \(checks) production Keychain query checks at Security boundary")
    }
}
