import Foundation
import CoreGraphics

@main struct Tests {
    static func main() {
        for width in [CGFloat(320), 375, 393, 430, 844] {
            for inset in [CGFloat(16), 20, 32] {
                let field = CGRect(x: 8, y: 0, width: width - 16, height: 36)
                guard let frame = NagramiXLanguageSearchLayout.frame(width: width, height: 56, left: inset, right: width - inset, field: field) else { fatalError("No frame") }
                let actualLeft = frame.minX + field.minX
                let actualRight = frame.maxX - (width - field.maxX)
                precondition(abs(actualLeft - inset) < 0.01)
                precondition(abs(actualRight - (width - inset)) < 0.01)
            }
        }
        precondition(NagramiXLanguageSearchLayout.frame(width: 0, height: 56, left: 16, right: 0, field: .zero) == nil)
        print("Геометрия поиска: проверки пройдены")
    }
}
