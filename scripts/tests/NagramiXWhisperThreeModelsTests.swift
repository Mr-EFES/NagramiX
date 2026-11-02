import Foundation

@main struct Tests {
    static func main() throws {
        let key = "nagramix.transcription.configuration.v1"
        let defaults = UserDefaults.standard
        let previous = defaults.data(forKey: key)
        defer { if let previous { defaults.set(previous, forKey: key) } else { defaults.removeObject(forKey: key) } }
        precondition(NagramiXTranscriptionConfiguration().whisper == .small_full)
        var value = NagramiXTranscriptionConfiguration()
        value.whisper = .base_full
        defaults.set(try JSONEncoder().encode(value), forKey: key)
        precondition(NagramiXTranscriptionSettings.current.whisper == .small_full)
        value.whisper = .medium
        defaults.set(try JSONEncoder().encode(value), forKey: key)
        precondition(NagramiXTranscriptionSettings.current.whisper == .medium)
        value.whisper = .large_v3
        defaults.set(try JSONEncoder().encode(value), forKey: key)
        precondition(NagramiXTranscriptionSettings.current.whisper == .large_v3)
        print("Whisper model migration tests passed")
    }
}
