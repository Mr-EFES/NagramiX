final class Layer {
    func animateAlpha(from: Double, to: Double, duration: Double, completion: @escaping (Bool) -> Void) {}
}
final class View {
    var alpha: Double = 1
    let layer = Layer()
}
final class Gallery {
    let view = View()
}
enum Dismissal { case pip }
final class PiPView {
    var nagramiXPiPRestoring = false
    func beginCustomDismiss(_ value: Dismissal) {}
    func completeCustomDismiss(_ value: Bool) {}
    func request(_ gallery: Gallery) {
        let callback: () -> Void = /* ACTUAL_DID_START */
        callback()
    }
}
