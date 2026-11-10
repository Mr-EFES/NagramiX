"""Реальная подготовка и wiring замены кружка; UIKit/декодер — адаптеры."""
from pathlib import Path
from validate_quick_format import block
from round_native_playback_runtime import ROUND, CHECK

ROOT = Path(__file__).resolve().parents[1]


def fixture(source):
    text = (source / ROUND).read_text()
    helper = block(text, 'private func nagramiXPrepareInstantVideoReplacement(')
    alias = next(x for x in text.splitlines() if x.startswith('private typealias NagramiXInstantVideoReplacementGeometry'))
    snapshot = next(x for x in text.splitlines() if 'let previousVideoGeometry = previousVideoNode.map' in x)
    start = text.index(snapshot)
    end = text.index('                            let mediaManager = ', start)
    removal = block(text[start:end], '                            if let videoNode = strongSelf.videoNode {')
    start = text.index('                            if let previousVideoNode = previousVideoNode {', end)
    end = text.index('                            strongSelf.nagramiXVideoUsesRetainedIdentity', start)
    prepare = text[start:end]
    start = text.index('                    if let videoNode = strongSelf.videoNode {', end)
    end = text.index('                    animation.animator.updateFrame(layer: strongSelf.secretVideoPlaceholderBackground', start)
    finish = text[start:end]
    return BOUNDARY + '\n' + alias + '\n' + helper + '\n' + '''
func replace(_ strongSelf: Row, archived: Bool, previouslyArchived: Bool, videoFrame: CGRect, displayVideoFrame: CGRect, targetScale: CGFloat, animation: Animation) -> UniversalVideoNode {
    let nagramiXArchivedInstantVideo = archived
    let imageScale = targetScale
    let arguments = Arguments(boundingSize: videoFrame.size)
    var previousVideoNode = strongSelf.videoNode
''' + snapshot + '\n' + removal + '\n    let videoNode = UniversalVideoNode()\n' + prepare + '''
    strongSelf.videoNode = videoNode
    videoNode.canAttachContent = strongSelf.shouldAcquireVideoContext
''' + finish + '\n return videoNode\n}\n' + CHECK + '\n' + (ROOT / 'scripts/tests/NagramiXRoundReplacementGeometryTests.swift').read_text()


BOUNDARY = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct CATransform3D: Equatable { var x: CGFloat; var y: CGFloat; var z: CGFloat }
func CATransform3DMakeScale(_ x: CGFloat, _ y: CGFloat, _ z: CGFloat) -> CATransform3D { .init(x: x, y: y, z: z) }
private extension CGRect { var center: CGPoint { CGPoint(x: midX, y: midY) } }
enum Transition { case immediate, animated }
struct Attachment { let bounds: CGRect; let position: CGPoint; let transform: CATransform3D; let contentSize: CGSize? }
final class UniversalVideoNode {
    var bounds: CGRect = .zero
    var position: CGPoint = .zero
    var transform = CATransform3DMakeScale(1, 1, 1)
    var layer: UniversalVideoNode { self }
    var allowsGroupOpacity = false
    var removed = false
    var layout: CGSize?
    var layoutTransitions: [Transition] = []
    var attachments: [Attachment] = []
    var canAttachContent = false {
        didSet {
            if canAttachContent && !oldValue { attachments.append(Attachment(bounds: bounds, position: position, transform: transform, contentSize: layout)) }
        }
    }
    func updateLayout(size: CGSize, transition: Transition) { layout = size; layoutTransitions.append(transition) }
    func removeFromSupernode() { removed = true }
    func animateAlpha(from: CGFloat, to: CGFloat, duration: Double, delay: Double, removeOnCompletion: Bool, completion: ((Bool) -> Void)?) { completion?(true) }
}
final class Animator {
    var scaleUpdates = 0
    var positionStarts: [CGPoint] = []
    func updateScale(layer: UniversalVideoNode, scale: CGFloat, completion: ((Bool) -> Void)?) { scaleUpdates += 1; layer.transform = CATransform3DMakeScale(scale, scale, 1) }
    func updatePosition(layer: UniversalVideoNode, position: CGPoint, completion: ((Bool) -> Void)?) { positionStarts.append(layer.position); layer.position = position }
}
struct Animation { let animator = Animator(); let transition = Transition.animated }
struct Arguments { let boundingSize: CGSize }
final class Row { var videoNode: UniversalVideoNode?; var imageScale: CGFloat = 0.5; var shouldAcquireVideoContext = true }
'''


def negatives(text):
    variants = [
        ('lost-predecessor', 'let previousVideoGeometry = previousVideoNode.map { (bounds: $0.bounds, position: $0.position, transform: $0.transform) }',
         'let previousVideoGeometry: NagramiXInstantVideoReplacementGeometry? = nil', 'replacement inherits removed predecessor position'),
        ('zero-inherited-position', 'videoNode.position = previous.position', 'videoNode.position = .zero', 'repeated archive replacement cannot restart at origin'),
        ('zero-fresh-position', 'videoNode.position = position', 'videoNode.position = .zero', 'fresh archived row attaches at target position'),
        ('late-decoration', 'videoNode.updateLayout(size: contentSize, transition: .immediate)', '_ = contentSize', 'decoration ready before decoder attachment'),
        ('skip-native-scale', 'return previous == nil', 'return true', 'native animator reaches target scale'),
        ('snap-inherited-scale', 'videoNode.transform = previous.transform', 'videoNode.transform = CATransform3DMakeScale(scale, scale, 1.0)', 'replacement keeps predecessor scale until native animation'),
    ]
    for name, before, after, diagnostic in variants:
        assert text.count(before) == 1, (name, text.count(before))
        yield name, text.replace(before, after), diagnostic
