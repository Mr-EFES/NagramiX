@main struct RoundReplacementGeometryTests {
    static func main() {
        for side in [202.0, 320.0, 404.0] {
            for scale in [0.5, 0.75, 1.0] {
                for archived in [false, true] {
                    for predecessor in [false, true] {
                        let row = Row()
                        let targetBounds = CGRect(x: 0, y: 0, width: side, height: side)
                        let target = CGRect(x: 0, y: 0, width: side * scale, height: side * scale)
                        let oldBounds = CGRect(x: 0, y: 0, width: 404, height: 404)
                        let oldPosition = CGPoint(x: 101.0 + 1.0 / 3.0, y: 101.0 + 2.0 / 3.0)
                        let oldScale: CGFloat = 0.5
                        let old: UniversalVideoNode?
                        if predecessor {
                            let node = UniversalVideoNode()
                            node.bounds = oldBounds; node.position = oldPosition
                            node.transform = CATransform3DMakeScale(oldScale, oldScale, 1)
                            node.canAttachContent = true
                            row.videoNode = node; old = node
                        } else { old = nil }
                        row.imageScale = oldScale
                        let animation = Animation()
                        // The other direction is an archive row reused for a live message.
                        let node = replace(row, archived: archived, previouslyArchived: !archived,
                            videoFrame: targetBounds, displayVideoFrame: target, targetScale: scale, animation: animation)
                        check(node.attachments.count == 1, "replacement attaches once")
                        let first = node.attachments[0]
                        if predecessor {
                            check(first.position == oldPosition, "replacement inherits removed predecessor position")
                            check(first.bounds == oldBounds, "replacement keeps prior bounds before animation")
                            check(first.transform == CATransform3DMakeScale(oldScale, oldScale, 1), "replacement keeps predecessor scale until native animation")
                            check(old!.removed && !old!.canAttachContent, "old moving surface detached and removed before replacement")
                        } else {
                            check(first.position == target.center, "fresh archived row attaches at target position")
                            check(first.bounds == targetBounds && first.transform == CATransform3DMakeScale(scale, scale, 1), "fresh row starts with complete target geometry")
                        }
                        check(first.contentSize == targetBounds.size, "decoration ready before decoder attachment")
                        check(node.position == target.center && node.bounds == targetBounds, "native animator reaches target position and bounds")
                        check(node.transform == CATransform3DMakeScale(scale, scale, 1), "native animator reaches target scale")
                        check(animation.animator.positionStarts.first == first.position, "animation begins at seeded pose")
                        check(animation.animator.scaleUpdates == (predecessor && scale != oldScale ? 1 : 0), "scale cache only skips an already seeded target")
                        check(node.layoutTransitions.count == 2, "immediate decoration then native animated layout")
                        // Replacing again must start where the preceding update ended.
                        let next = replace(row, archived: true, previouslyArchived: archived,
                            videoFrame: targetBounds, displayVideoFrame: target, targetScale: scale, animation: Animation())
                        check(next.attachments[0].position == node.position, "repeated archive replacement cannot restart at origin")
                        check(!node.canAttachContent && node.removed, "repeated replacement never keeps a second moving circle")
                    }
                }
            }
        }
        print("Round replacement geometry checks: \(checks)")
    }
}
