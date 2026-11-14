// Explicit model/storage/text-rendering boundary. Driver, metrics, spacing,
// audio/document row construction and header policy come from actual source.
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif

let UIScreenScale:CGFloat=3
struct UIEdgeInsets {let top:CGFloat,left:CGFloat,bottom:CGFloat,right:CGFloat}
enum RichText:Equatable {case empty,plain(String)}
struct InstantPageCaption {var text:RichText = .empty;var credit:RichText = .empty}
enum InstantPageBlock {
 case anchor(String),audio(Int,InstantPageCaption),document(Int,InstantPageCaption)
 case image(Int,InstantPageCaption,Int?,Int?,Bool),video(Int,InstantPageCaption,Bool,Bool,Bool)
 case slideshow([Int],InstantPageCaption),collage([Int],InstantPageCaption),map(Int,Int,Int,Int,InstantPageCaption)
 case paragraph(String),heading,thinking,list,table,details,preformatted,unsupported,cover,channelBanner,relatedArticles,divider,buttonRow
}
func blockRendersAsUnsupported(_ b:InstantPageBlock)->Bool{if case .unsupported=b{return true};return false}
struct File {}
enum EngineMedia {case file(File)}
struct TelegramMediaWebpage {}
struct InstantPageMedia {let index:Int;let media:EngineMedia;let url:String?,caption:String?,credit:String?}
struct InstantPageV2MediaAudioItem {var frame:CGRect;let media:InstantPageMedia;let webPage:TelegramMediaWebpage}
struct InstantPageV2DocumentItem {var frame:CGRect;let media:InstantPageMedia;let webPage:TelegramMediaWebpage}
struct Details {var frame:CGRect;let index:Int}
enum InstantPageV2LaidOutItem {
 case mediaAudio(InstantPageV2MediaAudioItem),document(InstantPageV2DocumentItem),text(CGRect),details(Details)
 var frame:CGRect{switch self{case let .mediaAudio(v):return v.frame;case let .document(v):return v.frame;case let .text(v):return v;case let .details(v):return v.frame}}
 func offsetBy(_ p:CGPoint)->Self{switch self{
 case var .mediaAudio(v):v.frame=v.frame.offsetBy(dx:p.x,dy:p.y);return .mediaAudio(v)
 case var .document(v):v.frame=v.frame.offsetBy(dx:p.x,dy:p.y);return .document(v)
 case let .text(v):return .text(v.offsetBy(dx:p.x,dy:p.y))
 case var .details(v):v.frame=v.frame.offsetBy(dx:p.x,dy:p.y);return .details(v)
 }}
}
struct InstantPageV2Layout {
 let contentSize:CGSize,items:[InstantPageV2LaidOutItem],detailsIndices:[Int],media:[Int:EngineMedia],webpage:TelegramMediaWebpage
}
struct InstantPageV2ChildBleed {let minXSide:CGFloat,maxXSide:CGFloat;static let none=Self(minXSide:0,maxXSide:0)}
struct ContainerStyle {var minimumMediaCornerRadius:CGFloat=0}
struct LayoutContext {
 var metrics=InstantPageMetrics.unscaled
 var childBleed=InstantPageV2ChildBleed.none
 var containerStyle=ContainerStyle()
 var edgeSpacingReduction:CGFloat=2
 var leadingFileInset:CGFloat=15
 var mediaIndexCounter=0
 var fitToWidth=true
 var media:[Int:EngineMedia]=[1:.file(File())]
 var webpage=TelegramMediaWebpage()
}
func instantPageV2BlockGap(_ spacing:CGFloat,upper:InstantPageBlock?,lower:InstantPageBlock,style:ContainerStyle)->CGFloat{spacing}
func redundantUnsupportedBlockIndices(_ blocks:[InstantPageBlock])->Set<Int>{[]}
func instantPageV2FitWidthMaxX(_ item:InstantPageV2LaidOutItem)->CGFloat{item.frame.maxX}
func instantPageV2StretchCodeBands(in items:inout [InstantPageV2LaidOutItem],contentWidth:CGFloat){}
func centerBlockFormulas(in items:inout [InstantPageV2LaidOutItem],contentWidth:CGFloat,horizontalInset:CGFloat){}
func layoutCaptionAndCredit(_ caption:InstantPageCaption,offset:CGFloat,boundingWidth:CGFloat,horizontalInset:CGFloat,context:inout LayoutContext)->([InstantPageV2LaidOutItem],CGFloat){
 guard caption.text != .empty else{return([],0)}
 let frame=CGRect(x:horizontalInset,y:offset+context.metrics.captionTopPad,width:boundingWidth-2*horizontalInset,height:24)
 return([.text(frame)],frame.maxY-offset)
}
