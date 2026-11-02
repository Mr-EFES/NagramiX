private let pictureInPictureImage = UIImage(bundleImageName: "Media Gallery/PictureInPictureIcon")?.precomposed()
private let pictureInPictureButtonImage = generateTintedImage(image: UIImage(bundleImageName: "Media Gallery/PictureInPictureButton"), color: .white)
private let moreButtonImage = generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/More"), color: .white)

private let placeholderFont = Font.regular(16.0)

private final class UniversalVideoGalleryItemPictureInPictureNode: ASDisplayNode {
    enum Mode {
        case pictureInPicture
    }
    
    private let iconNode: ASImageNode
    private let textNode: ASTextNode
    
    init(strings: PresentationStrings, mode: Mode) {
        self.iconNode = ASImageNode()
        self.iconNode.isLayerBacked = true
        self.iconNode.displayWithoutProcessing = true
        self.iconNode.displaysAsynchronously = false
        self.iconNode.image = pictureInPictureImage
        
        self.textNode = ASTextNode()
        self.textNode.isUserInteractionEnabled = false
        self.textNode.displaysAsynchronously = false
        
        let text: String
        switch mode {
        case .pictureInPicture:
            text = strings.Embed_PlayingInPIP
        }
        self.textNode.attributedText = NSAttributedString(string: text, font: placeholderFont, textColor: UIColor(rgb: 0x8e8e93))
        
        super.init()
        
        self.backgroundColor = UIColor(rgb: 0x333335)
        
        self.addSubnode(self.iconNode)
        self.addSubnode(self.textNode)
    }
    
    func updateLayout(_ size: CGSize, transition: ContainedViewLayoutTransition) {
        let iconSize = self.iconNode.image?.size ?? CGSize()
        let textSize = self.textNode.measure(CGSize(width: max(0.0, size.width - 20.0), height: CGFloat.greatestFiniteMagnitude))
        let spacing: CGFloat = 10.0
        let contentHeight = iconSize.height + spacing + textSize.height
        let contentVerticalOrigin = floor((size.height - contentHeight) / 2.0)
        transition.updateFrame(node: self.iconNode, frame: CGRect(origin: CGPoint(x: floor((size.width - iconSize.width) / 2.0), y: contentVerticalOrigin), size: iconSize))
        transition.updateFrame(node: self.textNode, frame: CGRect(origin: CGPoint(x: floor((size.width - textSize.width) / 2.0), y: contentVerticalOrigin + iconSize.height + spacing), size: textSize))
    }
}

