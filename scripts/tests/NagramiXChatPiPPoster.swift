// The validator inserts the production functions and the queued ready callback below.
import Foundation

private protocol EngineRawMedia {}
private struct EngineRawMessage { let media: [EngineRawMedia] }
private struct TelegramMediaImage: EngineRawMedia {
    let representations: [Int]
    var video: Int? = nil
}
private struct TelegramMediaFile: EngineRawMedia {
    let fileId: Int
    var isVideo = true
    var videoCover: TelegramMediaImage?
    var previewRepresentations: [Int] = []
    var immediateThumbnailData: Data?
}
private struct Page { let file: TelegramMediaFile?; let image: TelegramMediaImage? }
private enum PageContent { case Loaded(Page), pending }
private struct TelegramMediaWebpage: EngineRawMedia { let content: PageContent }
private struct WebpageReference { init(_ page: TelegramMediaWebpage) {} }
private enum ImageMediaReference { case webPage(webPage: WebpageReference, media: TelegramMediaImage) }
private struct EngineMedia {
    let value: EngineRawMedia
    func _asMedia() -> EngineRawMedia { value }
}
// POSTER

private final class UniversalVideoNode {
    var isHidden = false
    var alpha = 0.0
    var ownsContentNode = false
    var ownsContentNodeUpdated: ((Bool) -> Void)?
    var seeks: [Double] = []
    var plays = 0
    func transfer(_ owned: Bool) {
        guard ownsContentNode != owned else { return }
        ownsContentNode = owned
        ownsContentNodeUpdated?(owned)
    }
    func seek(_ timestamp: Double) { seeks.append(timestamp) }
    func setBaseRate(_ rate: Double) { precondition(rate == 1.0) }
    enum EndAction { case stop }
    func continuePlayingWithoutSound(actionAtEnd: EndAction? = nil) { plays += 1 }
}
private final class Container {
    var last: UniversalVideoNode?
    func insertSubnode(_ node: UniversalVideoNode, aboveSubnode: Int) { last = node }
}
private struct Pinch { let contentNode = Container() }
private final class Dispatcher {
    var actions: [() -> Void] = []
    func dispatch(_ action: @escaping () -> Void) { actions.append(action) }
    func flush() { actions.forEach { $0() }; actions.removeAll() }
}
private final class Cell {
    var videoNode: UniversalVideoNode?
    var media: EngineMedia?
    let pinchContainerNode = Pinch()
    let imageNode = 1
    let queue = Dispatcher()
    // OWNERSHIP

    func display(_ node: UniversalVideoNode) {
        videoNode = node
        configureInlineVideo(node, initialTimestamp: 17)
    }
    func ready(_ node: UniversalVideoNode) {
        let displayLinkDispatcher = queue
        let callback: () -> Void = { [weak strongSelf = self, weak videoNode = node] in
            // READY
        }
        callback()
    }
}

@main private enum Checks {
    static func main() {
        let cell = Cell()
        let first = UniversalVideoNode()
        cell.display(first)
        first.transfer(false) // PiP already owns the decoder when this cell appears.
        cell.ready(first)
        cell.queue.flush()
        precondition(cell.pinchContainerNode.contentNode.last === first && first.isHidden && first.plays == 0)
        first.transfer(true)
        precondition(!first.isHidden && first.seeks == [17] && first.plays == 1)
        first.transfer(false)
        precondition(first.isHidden)
        first.transfer(true)
        precondition(!first.isHidden && first.seeks == [17] && first.plays == 2)

        cell.ready(first)
        let next = UniversalVideoNode()
        cell.display(next)
        cell.pinchContainerNode.contentNode.last = nil
        cell.queue.flush()
        precondition(cell.pinchContainerNode.contentNode.last == nil)
        first.transfer(false)
        first.transfer(true)
        precondition(next.isHidden && next.plays == 0 && first.plays == 2)
        next.transfer(true)
        cell.ready(next)
        cell.queue.flush()
        precondition(!next.isHidden && cell.pinchContainerNode.contentNode.last === next)
        next.transfer(false)
        precondition(next.isHidden)

        var file = TelegramMediaFile(fileId: 1)
        let photo = TelegramMediaImage(representations: [41])
        let item = EngineRawMessage(media: [TelegramMediaWebpage(content: .Loaded(Page(file: file, image: photo)))])
        guard case let .webPage(_, image)? = webpageVideoPoster(message: item, media: file) else { preconditionFailure() }
        precondition(image.representations == [41])
        precondition(webpageVideoPoster(message: item, media: TelegramMediaFile(fileId: 2)) == nil)
        precondition(webpageVideoPoster(message: nil, media: file) == nil)
        file.previewRepresentations = [1]
        precondition(webpageVideoPoster(message: item, media: file) == nil)
        file.previewRepresentations = []
        file.videoCover = photo
        precondition(webpageVideoPoster(message: item, media: file) == nil)
        file.videoCover = nil
        file.immediateThumbnailData = Data([2])
        precondition(webpageVideoPoster(message: item, media: file) == nil)
        print("PASS chat PiP poster: no initial ownership, release, restore, reused cell, delayed ready and matching webpage cover")
    }
}
