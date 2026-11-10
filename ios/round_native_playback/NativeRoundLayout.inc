    func updateLayout(size: CGSize, actualSize: CGSize, transition: ContainedViewLayoutTransition) {
        self.validLayout = (size, actualSize)
        
        if let dimensions = self.dimensions {
            let imageSize = CGSize(width: floor(dimensions.width / 2.0), height: floor(dimensions.height / 2.0))
            let makeLayout = self.imageNode.asyncLayoutWithAnimation()
            let applyLayout = makeLayout(TransformImageArguments(corners: ImageCorners(), imageSize: imageSize, boundingSize: imageSize, intrinsicInsets: UIEdgeInsets(), emptyColor: self.fileReference.media.isInstantVideo ? .clear : self.placeholderColor))
            let mappedAnimation: ListViewItemUpdateAnimation
            if case let .animated(duration, curve) = transition {
                mappedAnimation = .System(duration: duration, transition: ControlledTransition(duration: duration, curve: curve, interactive: false))
            } else {
                mappedAnimation = .None
            }
            applyLayout(mappedAnimation)
        }
        
        transition.updateFrame(node: self.imageNode, frame: CGRect(origin: CGPoint(), size: size))
        let fromFrame = self.playerNode.frame
        let toFrame = CGRect(origin: CGPoint(), size: size).insetBy(dx: -1.0, dy: -1.0)
        if case let .animated(duration, curve) = transition, fromFrame != toFrame, !fromFrame.width.isZero, !fromFrame.height.isZero, !toFrame.width.isZero, !toFrame.height.isZero {
            let _ = duration
            let _ = curve
            self.playerNode.position = toFrame.center
            self.playerNode.bounds = CGRect(origin: CGPoint(), size: toFrame.size)
            self.playerNode.updateLayout()
            transition.animatePosition(node: self.playerNode, from: CGPoint(x: fromFrame.center.x, y: fromFrame.center.y))
            
            let transform = CATransform3DScale(CATransform3DIdentity, fromFrame.width / toFrame.width, fromFrame.height / toFrame.height, 1.0)
            self.playerNode.layer.animate(from: NSValue(caTransform3D: transform), to: NSValue(caTransform3D: CATransform3DIdentity), keyPath: "transform", timingFunction: curve.timingFunction, duration: duration)
        } else {
            transition.updatePosition(node: self.playerNode, position: toFrame.center)
            transition.updateBounds(node: self.playerNode, bounds: CGRect(origin: CGPoint(), size: toFrame.size))
            self.playerNode.updateLayout()
        }
        if let thumbnailNode = self.thumbnailNode {
            transition.updateFrame(node: thumbnailNode, frame: CGRect(origin: CGPoint(), size: size).insetBy(dx: -1.0, dy: -1.0))
        }
    }
