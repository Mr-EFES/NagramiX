// UI/Texture/measurement/presentation are explicit boundaries, no pixels.
var fixtureGlassAvailable=true
let containerInsets=UIEdgeInsets(top:10,left:10,bottom:10,right:10)
enum UIUserInterfaceStyle{case light,dark}
enum UIUserInterfaceLayoutDirection{case leftToRight,rightToLeft}
enum UIViewContentMode{case scaleAspectFit}
enum NSTextAlignment{case natural}
struct UIAccessibilityTraits:OptionSet{let rawValue:Int;static let header=Self(rawValue:1),button=Self(rawValue:2),selected=Self(rawValue:4),staticText=Self(rawValue:8)}
class UIFont {let size:CGFloat;init(_ size:CGFloat){self.size=size}}
enum Font{static func regular(_ size:CGFloat)->UIFont{UIFont(size)};static func semibold(_ size:CGFloat)->UIFont{UIFont(size)}}
class UILabel:UIView {
 var text:String?,font:UIFont?,textColor:UIColor?;var numberOfLines=1;var textAlignment=NSTextAlignment.natural
 func sizeThatFits(_ size:CGSize)->CGSize{let font=font?.size ?? 17;let width=CGFloat((text ?? "").utf16.count)*font*0.52;return CGSize(width:min(size.width,width),height:ceil(max(1,width/max(1,size.width)))*font*1.2)}
}
class UIButton:UIView {
 enum ButtonType{case system};enum State{case normal};enum Event{case touchUpInside}
 var tintColor:UIColor?;var isEnabled=true
 convenience init(type:ButtonType){self.init()}
 func setImage(_ image:UIImage?,for state:State){}
 func addTarget(_ target:AnyObject,action:String,for event:Event){}
}
class HighlightTrackingButton:UIButton {var highligthedChanged:((Bool)->Void)?}
protocol ActionSheetItem {func node(theme:ActionSheetControllerTheme)->ActionSheetItemNode;func updateNode(_ node:ActionSheetItemNode)}
struct ActionSheetItemGroup{let items:[ActionSheetItem]}
class ActionSheetController {
 var nagramiXBottomAttached=false;var dismissed:((Bool)->Void)?;var groups:[ActionSheetItemGroup]=[];var dismissals=0
 init(presentationData:PresentationData){}
 func dismissAnimated(){dismissals+=1;dismissed?(false)}
 func setItemGroups(_ groups:[ActionSheetItemGroup]){self.groups=groups}
}
class FixtureGroups{var groupNodes:[ActionSheetItemGroupNode]=[]}
struct PresentationStrings {
 var nagramiXOptionSheetClose="Закрыть",nagramiXDns="DNS-сервер"
 var nagramiXDnsSystem="Системный",nagramiXDnsTelegram="Telegram",nagramiXDnsGoogle="Google",nagramiXDnsAdGuard="AdGuard",nagramiXDnsCloudflare="Cloudflare",nagramiXDnsCustom="Пользовательский DoH"
 var nagramiXDownloadMedium="Среднее",nagramiXDownloadMaximum="Максимум",nagramiXDownloadMediumInfo="Умеренная нагрузка на сеть",nagramiXDownloadMaximumInfo="Повышенная нагрузка на сеть",nagramiXDownloadAccelerationMode="Параметры скачивания"
 func nagramiXLocalized(_ key:String)->String{key}
}
struct PresentationData{let strings=PresentationStrings()}
struct FixtureAtomic{func with<T>(_ body:(PresentationData)->T)->T{body(PresentationData())}}
struct FixtureShared{let currentPresentationData=FixtureAtomic()}
struct FixtureContext{let sharedContext=FixtureShared()}
let context=FixtureContext();let sharedContext=FixtureShared()
struct FixtureDownloads{var enabled=true;var mode=NagramiXDownloadAcceleration.medium}
struct FixtureSettings{var downloads=FixtureDownloads();var dnsProvider=NagramiXDnsProvider.telegram;var customDohUrl=""}
enum NagramiXTabSettings{static var current=FixtureSettings()}
struct FixtureTyping{var enabled=true;var preset=NagramiXTypingPreset.wave}
enum NagramiXTypingSettings{static var current=FixtureTyping();static func update(_ body:(inout FixtureTyping)->Void){body(&current)}}
class FixturePromise{var calls=0;func set(_ value:FixtureSettings){calls+=1}}
let settingsPromise=FixturePromise()
func update(_ body:(inout FixtureSettings)->Void){body(&NagramiXTabSettings.current)}
func updateNagramiXSettings(_ body:(inout FixtureSettings)->Void){body(&NagramiXTabSettings.current)}
var presented:ActionSheetController?
var presentControllerImpl:((ActionSheetController)->Void)?={presented=$0}
var editorOpens=0
var editCustomDohImpl:(()->Void)?={editorOpens+=1}
