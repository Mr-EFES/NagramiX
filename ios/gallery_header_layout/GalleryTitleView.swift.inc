import Foundation
import UIKit
import AsyncDisplayKit
import Display
import TelegramCore
import AccountContext
import TelegramPresentationData
import TelegramStringFormatting
import GlassBackgroundComponent
import ComponentFlow
import ComponentDisplayAdapters
import MultilineTextComponent

private let titleFont = Font.semibold(17.0)
private let dateFont = Font.regular(12.0)

public final class GalleryTitleView: UIView, NavigationBarTitleView {
    public final class Content: Equatable {
        let message: EngineMessage?
        let authorTitle: String?
        let dateTitle: String?
        let title: String?
        let action: (() -> Void)?

        public init(message: EngineMessage, title: String?, action: (() -> Void)?) {
            self.message = message
            self.authorTitle = nil
            self.dateTitle = nil
            self.title = title
            self.action = action
        }

        public init(authorTitle: String?, dateTitle: String?, title: String?, action: (() -> Void)?) {
            self.message = nil
            self.authorTitle = authorTitle
            self.dateTitle = dateTitle
            self.title = title
            self.action = action
        }
        
        public static func ==(lhs: Content, rhs: Content) -> Bool {
            if lhs.message != rhs.message {
                return false
            }
            if lhs.authorTitle != rhs.authorTitle {
                return false
            }
            if lhs.dateTitle != rhs.dateTitle {
                return false
            }
            if lhs.title != rhs.title {
                return false
            }
            if (lhs.action == nil) != (rhs.action == nil) {
                return false
            }
            return true
        }
    }
    
    private let context: AccountContext
    private let presentationData: PresentationData
    
    private let backgroundContainer: GlassBackgroundContainerView
    private let backgroundView: GlassBackgroundView
    private let authorNameNode: ASTextNode
    private let dateNode: ASTextNode
    
    private let titleBackgroundContainer: GlassBackgroundContainerView
    private let titleBackground: GlassBackgroundView
    private let title = ComponentView<Empty>()
    
    private var content: Content?
    private var titleString: String?
    
    // Use the actual gap between the leading and trailing button groups, including asymmetric layouts.
    public internal(set) var alignedContentInsets: UIEdgeInsets?
    public var requestUpdate: ((ContainedViewLayoutTransition) -> Void)?
    
    private var interactionTimer: Foundation.Timer?
    
    public init(context: AccountContext, presentationData: PresentationData) {
        self.context = context
        self.presentationData = presentationData
        
        self.backgroundContainer = GlassBackgroundContainerView()
        self.backgroundView = GlassBackgroundView()
        self.backgroundContainer.contentView.addSubview(self.backgroundView)
        
        self.authorNameNode = ASTextNode()
        self.authorNameNode.isUserInteractionEnabled = false
        self.authorNameNode.displaysAsynchronously = false
        self.authorNameNode.maximumNumberOfLines = 1
        
        self.dateNode = ASTextNode()
        self.dateNode.isUserInteractionEnabled = false
        self.dateNode.displaysAsynchronously = false
        self.dateNode.maximumNumberOfLines = 1
        
        self.titleBackgroundContainer = GlassBackgroundContainerView()
        self.titleBackground = GlassBackgroundView()
        
        self.titleBackgroundContainer.contentView.addSubview(self.titleBackground)
        
        super.init(frame: CGRect())
        
        self.addSubview(self.backgroundContainer)
        
        self.backgroundView.contentView.addSubview(self.authorNameNode.view)
        self.backgroundView.contentView.addSubview(self.dateNode.view)
        
        self.backgroundContainer.isHidden = true
        
        self.addSubview(self.titleBackgroundContainer)
        self.titleBackgroundContainer.alpha = 0.0
        
        self.backgroundView.contentView.addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(self.onTapGesture(_:))))
    }
    
    required public init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    deinit {
        self.interactionTimer?.invalidate()
    }
    
    @objc private func onTapGesture(_ recognizer: UITapGestureRecognizer) {
        if case .ended = recognizer.state {
            self.content?.action?()
        }
    }
    
    public func setContent(content: Content?) {
        self.content = content
        
        let authorNameText: String?
        let dateText: String?
        
        if let content {
            if let message = content.message {
                authorNameText = stringForFullAuthorName(message: message, strings: self.presentationData.strings, nameDisplayOrder: self.presentationData.nameDisplayOrder, accountPeerId: self.context.account.peerId).first ?? ""
                dateText = humanReadableStringForTimestamp(strings: self.presentationData.strings, dateTimeFormat: self.presentationData.dateTimeFormat, timestamp: message.timestamp).string
            } else {
                authorNameText = content.authorTitle
                dateText = content.dateTitle
            }
        } else {
            authorNameText = nil
            dateText = nil
        }

        if let authorNameText {
            self.authorNameNode.attributedText = NSAttributedString(string: authorNameText, font: titleFont, textColor: .white)
        } else {
            self.authorNameNode.attributedText = nil
        }

        if let dateText {
            self.dateNode.attributedText = NSAttributedString(string: dateText, font: dateFont, textColor: UIColor(white: 1.0, alpha: 0.5))
        } else {
            self.dateNode.attributedText = nil
        }

        self.backgroundContainer.isHidden = (authorNameText?.isEmpty ?? true) && (dateText?.isEmpty ?? true)
        
        // VoiceOver: the title is one heading, "author, date", as shown.
        let accessibilityTitle = [authorNameText, dateText].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")
        self.isAccessibilityElement = !accessibilityTitle.isEmpty
        self.accessibilityLabel = accessibilityTitle.isEmpty ? nil : accessibilityTitle
        self.accessibilityTraits = .header

        self.titleString = content?.title

        if !self.bounds.isEmpty {
            let _ = self.updateLayout(availableSize: self.bounds.size, transition: .immediate)
        }
    }
    
    public func updateLayout(availableSize: CGSize, transition: ContainedViewLayoutTransition) -> CGSize {
        let size = CGSize(width: max(0, availableSize.width), height: max(0, availableSize.height))
        self.isHidden = size.width < 1 || size.height < 1
        guard !self.isHidden else { return size }

        let padding = min(14.0, size.width / 4)
        let textWidth = max(1, size.width - 2 * padding)
        let constraint = CGSize(width: textWidth, height: CGFloat.greatestFiniteMagnitude)
        let authorNameSize = self.authorNameNode.measure(constraint)
        let dateSize = self.dateNode.measure(constraint)
        let measuredWidth = max(authorNameSize.width, dateSize.width)
        let backgroundSize = CGSize(width: min(size.width, max(178, measuredWidth + 2 * padding)), height: min(44, size.height))

        if authorNameSize.height.isZero {
            self.authorNameNode.frame = .zero
            self.dateNode.frame = CGRect(origin: CGPoint(x: floor((backgroundSize.width - dateSize.width) / 2.0), y: floor((backgroundSize.height - dateSize.height) / 2.0)), size: dateSize)
        } else {
            let labelsSpacing: CGFloat = 2.0
            self.authorNameNode.frame = CGRect(origin: CGPoint(x: floor((backgroundSize.width - authorNameSize.width) / 2.0), y: floor((backgroundSize.height - dateSize.height - authorNameSize.height - labelsSpacing) / 2.0)), size: authorNameSize)
            self.dateNode.frame = CGRect(origin: CGPoint(x: floor((backgroundSize.width - dateSize.width) / 2.0), y: floor((backgroundSize.height - dateSize.height - authorNameSize.height - labelsSpacing) / 2.0) + authorNameSize.height + labelsSpacing), size: dateSize)
        }
        
        let backgroundFrame = CGRect(origin: CGPoint(x: floor((size.width - backgroundSize.width) * 0.5), y: floor((size.height - backgroundSize.height) * 0.5)), size: backgroundSize)
        
        self.backgroundContainer.update(size: backgroundFrame.size, isDark: true, transition: ComponentTransition(transition))
        ComponentTransition(transition).setFrame(view: self.backgroundContainer, frame: backgroundFrame)
        
        ComponentTransition(transition).setFrame(view: self.backgroundView, frame: CGRect(origin: CGPoint(), size: backgroundFrame.size))
        self.backgroundView.update(size: backgroundSize, cornerRadius: backgroundSize.height * 0.5, isDark: true, tintColor: .init(kind: .panel), isInteractive: self.content?.action != nil, transition: ComponentTransition(transition))
        
        let titleInset = min(12.0, size.width / 4)
        let titleSize = self.title.update(
            transition: .immediate,
            component: AnyComponent(MultilineTextComponent(
                text: .plain(NSAttributedString(string: self.titleString ?? "", font: Font.semibold(12.0), textColor: .white))
            )),
            environment: {},
            containerSize: CGSize(width: min(200, size.width - titleInset * 2), height: 24)
        )
        let titleBackgroundSize = CGSize(width: min(size.width, titleInset * 2 + titleSize.width), height: 24)
        let titleBackgroundFrame = CGRect(origin: CGPoint(x: floorToScreenPixels((availableSize.width - titleBackgroundSize.width) * 0.5), y: availableSize.height + 2.0), size: titleBackgroundSize)
        let titleFrame = titleSize.centered(in: CGRect(origin: CGPoint(), size: titleBackgroundSize))
        if let titleView = self.title.view {
            if titleView.superview == nil {
                self.titleBackground.contentView.addSubview(titleView)
            }
            titleView.frame = titleFrame
        }
        
        do {
            let transition = ComponentTransition.immediate
            transition.setFrame(view: self.titleBackgroundContainer, frame: titleBackgroundFrame)
            self.titleBackgroundContainer.update(size: titleBackgroundSize, isDark: true, transition: transition)
            
            transition.setFrame(view: self.titleBackground, frame: CGRect(origin: CGPoint(), size: titleBackgroundSize))
            self.titleBackground.update(size: titleBackgroundSize, cornerRadius: titleBackgroundSize.height * 0.5, isDark: true, tintColor: .init(kind: .panel), transition: transition)
            
            self.titleBackgroundContainer.isHidden = !(self.titleString != nil && self.titleString != "")
        }
        
        return size
    }
    
    public func animateLayoutTransition() {
    }
    
    public func updateIsInteracting(isInteracting: Bool) {
        if isInteracting {
            self.interactionTimer?.invalidate()
            self.interactionTimer = nil
            
            ComponentTransition.easeInOut(duration: 0.2).animateView {
                self.titleBackgroundContainer.alpha = 1.0
            }
        } else {
            self.interactionTimer?.invalidate()
            self.interactionTimer = Foundation.Timer.scheduledTimer(withTimeInterval: 2.0, repeats: false, block: { [weak self] _ in
                guard let self else {
                    return
                }
                ComponentTransition.easeInOut(duration: 0.2).animateView {
                    self.titleBackgroundContainer.alpha = 0.0
                }
            })
        }
    }
}
