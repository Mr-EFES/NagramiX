import Foundation
import UIKit
import AsyncDisplayKit
import Display
import SwiftSignalKit
import UniversalMediaPlayer
import AccountContext
import PhotoResources

public final class GalleryVideoDecoration: UniversalVideoDecoration {
    public let backgroundNode: ASDisplayNode? = nil
    public let contentContainerNode: ASDisplayNode
    public let foregroundNode: ASDisplayNode? = nil
    
    private var contentNode: (ASDisplayNode & UniversalVideoContentNode)?
    private var contentNodeSnapshot: UIView?
    
    private var validLayout: (size: CGSize, actualSize: CGSize)?
    private var nagramiXPiPTransitionActive = false
    private var nagramiXDeferredCorners: ImageCorners?

    public func setNagramiXPiPTransitionActive(_ active: Bool) {
        guard self.nagramiXPiPTransitionActive != active else { return }
        self.nagramiXPiPTransitionActive = active
        if !active {
            if let corners = self.nagramiXDeferredCorners {
                self.nagramiXDeferredCorners = nil
                self.updateCorners(corners)
            }
            if let layout = self.validLayout {
                self.updateLayout(size: layout.size, actualSize: layout.actualSize, transition: .immediate)
            }
        }
    }
    
    public init() {
        self.contentContainerNode = ASDisplayNode()
    }
    
    public func updateContentNode(_ contentNode: (UniversalVideoContentNode & ASDisplayNode)?) {
        if self.contentNode !== contentNode {
            let previous = self.contentNode
            self.contentNode = contentNode
            
            if let previous = previous {
                if previous.supernode === self.contentContainerNode {
                    previous.removeFromSupernode()
                }
            }
            
            if let contentNode = contentNode {
                if contentNode.supernode !== self.contentContainerNode {
                    self.contentContainerNode.addSubnode(contentNode)
                    if let validLayout = self.validLayout, !self.nagramiXPiPTransitionActive {
                        contentNode.frame = CGRect(origin: CGPoint(), size: validLayout.size)
                        contentNode.updateLayout(size: validLayout.size, actualSize: validLayout.actualSize, transition: .immediate)
                    }
                }
            }
        }
    }
    
    public func updateCorners(_ corners: ImageCorners) {
        if self.nagramiXPiPTransitionActive {
            self.nagramiXDeferredCorners = corners
            return
        }
        self.contentContainerNode.clipsToBounds = true
        if isRoundEqualCorners(corners) {
            self.contentContainerNode.cornerRadius = corners.topLeft.radius
        } else {
            let boundingSize: CGSize = CGSize(width: max(corners.topLeft.radius, corners.bottomLeft.radius) + max(corners.topRight.radius, corners.bottomRight.radius), height: max(corners.topLeft.radius, corners.topRight.radius) + max(corners.bottomLeft.radius, corners.bottomRight.radius))
            let size: CGSize = CGSize(width: boundingSize.width + corners.extendedEdges.left + corners.extendedEdges.right, height: boundingSize.height + corners.extendedEdges.top + corners.extendedEdges.bottom)
            let arguments = TransformImageArguments(corners: corners, imageSize: size, boundingSize: boundingSize, intrinsicInsets: UIEdgeInsets())
            guard let context = DrawingContext(size: size, clear: true) else {
                return
            }
            context.withContext { ctx in
                ctx.setFillColor(UIColor.black.cgColor)
                ctx.fill(arguments.drawingRect)
            }
            addCorners(context, arguments: arguments)
            
            if let maskImage = context.generateImage() {
                let mask = CALayer()
                mask.contents = maskImage.cgImage
                mask.contentsScale = maskImage.scale
                mask.contentsCenter = CGRect(x: max(corners.topLeft.radius, corners.bottomLeft.radius) / maskImage.size.width, y: max(corners.topLeft.radius, corners.topRight.radius) / maskImage.size.height, width: (maskImage.size.width - max(corners.topLeft.radius, corners.bottomLeft.radius) - max(corners.topRight.radius, corners.bottomRight.radius)) / maskImage.size.width, height: (maskImage.size.height - max(corners.topLeft.radius, corners.topRight.radius) - max(corners.bottomLeft.radius, corners.bottomRight.radius)) / maskImage.size.height)
                
                self.contentContainerNode.layer.mask = mask
                self.contentContainerNode.layer.mask?.frame = self.contentContainerNode.bounds
            }
        }
    }
    
    public func updateClippingFrame(_ frame: CGRect, completion: (() -> Void)?) {
        // A preview has no live layer to animate. Complete this branch as well;
        // otherwise the gallery's dismissal barrier waits forever.
        guard !self.nagramiXPiPTransitionActive, let contentNode = self.contentNode else {
            completion?()
            return
        }
        self.contentContainerNode.layer.animate(from: NSValue(cgRect: self.contentContainerNode.bounds), to: NSValue(cgRect: frame), keyPath: "bounds", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
        })

        if let maskLayer = self.contentContainerNode.layer.mask {
            maskLayer.animate(from: NSValue(cgRect: self.contentContainerNode.bounds), to: NSValue(cgRect: frame), keyPath: "bounds", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            })
            
            maskLayer.animate(from: NSValue(cgPoint: maskLayer.position), to: NSValue(cgPoint: frame.center), keyPath: "position", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            })
        }
        
        contentNode.layer.animate(from: NSValue(cgPoint: contentNode.layer.position), to: NSValue(cgPoint: frame.center), keyPath: "position", timingFunction: kCAMediaTimingFunctionSpring, duration: 0.25, removeOnCompletion: false, completion: { _ in
            completion?()
        })
    }
    
    public func updateContentNodeSnapshot(_ snapshot: UIView?) {
        guard self.contentNodeSnapshot !== snapshot else { return }
        self.contentNodeSnapshot?.removeFromSuperview()
        self.contentNodeSnapshot = snapshot
        if let snapshot {
            self.contentContainerNode.view.addSubview(snapshot)
            if let validLayout = self.validLayout {
                snapshot.frame = CGRect(origin: .zero, size: validLayout.size)
            }
        }
    }
    
    public func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {
        self.validLayout = (size, actualSize)
        // AVKit animates the original source rectangle. Defer client layout and
        // corner changes until the layer has returned or the handoff has ended.
        guard !self.nagramiXPiPTransitionActive else { return }
        
        let bounds = CGRect(origin: CGPoint(), size: size)
        if let backgroundNode = self.backgroundNode {
            transition.updateFrame(node: backgroundNode, frame: bounds)
        }
        if let foregroundNode = self.foregroundNode {
            transition.updateFrame(node: foregroundNode, frame: bounds)
        }
        transition.updateFrame(node: self.contentContainerNode, frame: bounds)
        if let contentNodeSnapshot = self.contentNodeSnapshot {
            transition.updateFrame(layer: contentNodeSnapshot.layer, frame: bounds)
        }
        if let maskLayer = self.contentContainerNode.layer.mask {
            transition.updateFrame(layer: maskLayer, frame: bounds)
        }
        if let contentNode = self.contentNode {
            transition.updateFrame(node: contentNode, frame: CGRect(origin: CGPoint(), size: size))
            contentNode.updateLayout(size: size, actualSize: actualSize, transition: transition)
        }
    }
    
    public func setStatus(_ status: Signal<MediaPlayerStatus?, NoError>) {
    }
    
    public func tap() {
    }
}
