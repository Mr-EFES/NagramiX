import Foundation

@main struct Tests {
    static func main() {
        func words(_ s: String) -> [Substring] { s.split(whereSeparator: { $0.isWhitespace }) }
        precondition(words(NagramiXWhisperLicense.rawText) == words(NagramiXWhisperLicense.text))
        precondition(words(NagramiXVoskLicense.rawText) == words(NagramiXVoskLicense.text))
        precondition(NagramiXWhisperLicense.text.contains("a copy of this software and associated documentation"))
        precondition(NagramiXVoskLicense.text.contains("terms and conditions for use, reproduction, and distribution as defined"))
        precondition(NagramiXVoskLicense.text.contains("Apache License\nVersion 2.0, January 2004\nhttp://www.apache.org/licenses/"))
        precondition(NagramiXLicenseLayout.reflow("  first line\n second line\n\n  next paragraph  ") == "first line second line\n\nnext paragraph")
        print("License text reflow tests passed")
    }
}
