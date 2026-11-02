import Foundation
import UIKit
import AsyncDisplayKit
import Display
import SwiftSignalKit

public enum GalleryItemNodeNavigationStyle {
    case light
    case dark
}

open class GalleryItemNode: ASDisplayNode {
    public enum ActiveEdge {
        case left
        case right
        case middle
    }
    
    private var _index: Int?
    public var index: Int {
        get {
            return self._index!
        } set(value) {
            self._index = value
        }
    }
    
    public var toggleControlsVisibility: () -> Void = { }
    public var updateControlsVisibility: (Bool) -> Void = { _ in }
    public var controlsVisibility: () -> Bool = { return true }
    public var updateOrientation: (UIInterfaceOrientation) -> Void = { _ in }
    public var dismiss: () -> Void = { }
    public var beginCustomDismiss: (GalleryControllerNode.CustomDismissType) -> Void = { _ in }
    public var completeCustomDismiss: (Bool) -> Void = { _ in }
    public var baseNavigationController: () -> NavigationController? = { return nil }
    public var galleryController: () -> ViewController? = { return nil }
    public var alternativeDismiss: () -> Bool = { return false }
    
    override public init() {
        super.init()
        
        self.setViewBlock({
            return UITracingLayerView()
        })
    }
    
    open func ready() -> Signal<Void, NoError> {
        return .single(Void())
    }
    
    open func title() -> Signal<String, NoError> {
        return .single("")
    }
    
    open func titleContent() -> Signal<GalleryTitleView.Content?, NoError> {
        return .single(nil)
    }
    
    open func rightBarButtonItem() -> Signal<UIBarButtonItem?, NoError> {
        return .single(nil)
    }
    
    open func rightBarButtonItems() -> Signal<[UIBarButtonItem]?, NoError> {
        return .single(nil)
    }
    
    open func isPagingEnabled() -> Signal<Bool, NoError> {
        return .single(true)
    }
    
    open func footerContent() -> Signal<(GalleryFooterContentNode?, GalleryOverlayContentNode?), NoError> {
        return .single((nil, nil))
    }
    
    open func navigationStyle() -> Signal<GalleryItemNodeNavigationStyle, NoError> {
        return .single(.dark)
    }
    
    open func containerLayoutUpdated(_ layout: ContainerViewLayout, navigationBarHeight: CGFloat, transition: ContainedViewLayoutTransition) {
    }
    
    open func centralityUpdated(isCentral: Bool) {
    }
    
    open func screenFrameUpdated(_ frame: CGRect) {
    }
    
    open func activateAsInitial() {
    }
    
    open func processAction(_ action: GalleryControllerItemNodeAction) {
    }
    
    open func visibilityUpdated(isVisible: Bool) {
    }
    
    open func controlsVisibilityUpdated(isVisible: Bool, animated: Bool) {
    }
    
    open func adjustForPreviewing() {
    }
    
    open func animateIn(from node: (ASDisplayNode, CGRect, () -> (UIView?, UIView?)), addToTransitionSurface: (UIView) -> Void, completion: @escaping () -> Void) {
    }
    
    open func animateOut(to node: (ASDisplayNode, CGRect, () -> (UIView?, UIView?)), addToTransitionSurface: (UIView) -> Void, completion: @escaping () -> Void) {
    }
    
    open var nagramiXPiPSwipeView: UIView { return self.view }

    open func nagramiXPiPSourceFrame(in view: UIView) -> CGRect {
        return self.view.convert(self.view.bounds, to: view)
    }

    open var nagramiXPiPNativeTransitionInFlight: Bool { return false }

    func nagramiXPictureInPictureRequestFailed() {}

    var nagramiXPiPSwipeTransitionPending = false

    open var nagramiXBlocksPiPSourcePan: Bool { return false }

    open var nagramiXCanBeginDirectionalPiPSwipe: Bool { return false }

    open func nagramiXRequireDirectionalPiPGesture(_ gesture: UIPanGestureRecognizer) {
    }

    open func nagramiXStartDirectionalPiP(completion: @escaping (Bool) -> Void) -> Bool {
        return false
    }

    // Only eligible video nodes opt into preparing AVKit during an explicit drag.
    open func prepareForPictureInPictureSwipe() -> Bool {
        return false
    }

    open func cancelPictureInPictureSwipePreparation() {
    }

    open func maybePerformActionForSwipeDismiss() -> Bool {
        return false
    }
    
    open func maybePerformActionForSwipeDownDismiss() -> Bool {
        return false
    }
    
    open func contentSize() -> CGSize? {
        return nil
    }
    
    open var keyShortcuts: [KeyShortcut] {
        return []
    }
    
    open func hasActiveEdgeAction(edge: ActiveEdge) -> Bool {
        return false
    }
    
    open func setActiveEdgeAction(edge: ActiveEdge?) {
    }
    
    open func adjustActiveEdgeAction(distance: CGFloat) {
    }
}
