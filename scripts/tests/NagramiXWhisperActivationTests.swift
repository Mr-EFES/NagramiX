import Foundation
@main struct Tests {
    static func main() {
        var c = NagramiXTranscriptionConfiguration()
        c.provider = .whisper; c.revision = "r1"
        precondition(!NagramiXWhisperActivationPolicy.permits(c, revision:"r1"))
        c.enabled = true
        precondition(NagramiXWhisperActivationPolicy.permits(c, revision:"r1"))
        precondition(!NagramiXWhisperActivationPolicy.permits(c, revision:"stale"))
        c.provider = .apple
        precondition(!NagramiXWhisperActivationPolicy.permits(c, revision:"r1"))
        c.provider = .whisper; c.revision = "new"
        precondition(!NagramiXWhisperActivationPolicy.permits(c, revision:"r1"))
        print("PASS: download activation respects enabled, provider and current revision")
    }
}
