"""Реальные настройки, SignalKit и выбор баннера в явных адаптерах моделей."""
from validate_quick_format import block

TAB='submodules/NagramiXCore/Sources/NagramiXTabSettings.swift'
UI='submodules/SettingsUI/Sources/NagramiXSettingsController.swift'
CONTEXT='submodules/TelegramUI/Components/GlobalControlPanelsContext/Sources/GlobalControlPanelsContext.swift'
BUILD='submodules/TelegramUI/Components/GlobalControlPanelsContext/BUILD'
SUGGESTIONS='submodules/TelegramCore/Sources/Suggestions.swift'
SK='submodules/SSignalKit/SwiftSignalKit/Source/'

CHECK=r'''
var checks=0
func check(_ value:@autoclosure()->Bool,_ message:String){if !value(){FileHandle.standardError.write(Data(("Premium offer regression: "+message+"\n").utf8));exit(91)};checks+=1}
'''


def preferences(source):
    text=block((source/TAB).read_text(),'public enum NagramiXPremiumOfferSettings {')
    return 'import Foundation\n'+CHECK+text+r'''
@main struct PreferenceTests {static func main(){
 if CommandLine.arguments.count==4 {
  let d=UserDefaults(suiteName:CommandLine.arguments[1])!
  let hidden=CommandLine.arguments[3]=="true"
  if CommandLine.arguments[2]=="write" {NagramiXPremiumOfferSettings.setHidden(hidden,in:d);check(d.synchronize(),"history persisted")}
  else{check(NagramiXPremiumOfferSettings.isHidden(in:d)==hidden,"saved checkbox survives cold process")}
  return
 }
 let suite="nagramix-premium-offer-"+UUID().uuidString;let d=UserDefaults(suiteName:suite)!
 defer{d.removePersistentDomain(forName:suite)}
 let key="nagramix.interface.hidePremiumOffers"
 check(NagramiXPremiumOfferSettings.isHidden(in:d),"cold install hides Premium banners")
 check(d.object(forKey:key)==nil,"reading default never writes an implicit choice")
 NagramiXPremiumOfferSettings.setHidden(false,in:d)
 check(!NagramiXPremiumOfferSettings.isHidden(in:d),"explicit OFF is preserved")
 d.set(false,forKey:"nagramix.tabs.hideContacts")
 check(!NagramiXPremiumOfferSettings.isHidden(in:d),"unrelated settings cannot reset saved OFF")
 check(!NagramiXPremiumOfferSettings.isHidden(in:UserDefaults(suiteName:suite)!),"new defaults instance retains OFF")
 NagramiXPremiumOfferSettings.setHidden(true,in:d)
 check(NagramiXPremiumOfferSettings.isHidden(in:d),"explicit ON is restored")
 print("Premium preference checks: \(checks)")
}}
'''


MODELS=r'''
public final class Queue {}
public func deliverOn<T,E>(_ queue:Queue)->(Signal<T,E>)->Signal<T,E>{{s in s}}
struct ServerSuggestionInfo {struct Item {typealias Text=String}}
struct EnginePeer:Equatable {typealias Id=Int;let id:Int;var addressName:String?="user";var smallProfileImage:Int?=1}
struct TelegramBirthday:Equatable {var today=true}
struct NewSessionReview:Equatable {let id:Int}
struct NewBotConnectionReview:Equatable {let botId:Int}
struct StarsAmount:Comparable {let value:Int;static let zero=Self(value:0);static func <(l:Self,r:Self)->Bool{l.value<r.value}}
struct PeerKey {let id:Int}
struct TelegramEngine {struct EngineData {struct Item {struct Peer {typealias Peer=PeerKey}}}}
struct EngineDataMap {let keys:[PeerKey];init(_ keys:[PeerKey]){self.keys=keys}}
enum RelativeBirthday {case today,other}
func relativeDateForBirthday(_ value:TelegramBirthday,relativeTo:Date,timeZone:TimeZone)->RelativeBirthday{value.today ? .today:.other}
struct FrozenConfiguration {var freezeUntilDate:Int?}
struct StarSubscription {let peer:EnginePeer}
struct StarState {var balance=StarsAmount(value:1);var subscriptions=[StarSubscription(peer:EnginePeer(id:8))]}
final class StarsSubscriptionsContext {var state:Signal<StarState,NoError>{.single(StarState())}}
final class StarsPromise {func set(_ v:Signal<StarsSubscriptionsContext?,NoError>) {}}
struct Product {let id:String;let priceCurrencyAndAmount:(currency:String,amount:Double);let priceValue:NSDecimalNumber}
final class ProductManager {var availableProducts:Signal<[Product],NoError> = .single([])}
enum GlobalExperimentalSettings {static var isAppStoreBuild=false}
final class DataEngine {
 var peers:[Int:EnginePeer]=[1:EnginePeer(id:1),8:EnginePeer(id:8)]
 var fetches=0
 func get(_ key:PeerKey)->Signal<EnginePeer?,NoError>{fetches+=1;return .single(peers[key.id])}
 func get(_ map:EngineDataMap)->Signal<[Int:EnginePeer?],NoError>{fetches+=1;var result:[Int:EnginePeer?]=[:];for key in map.keys{result[key.id] = .some(peers[key.id])};return .single(result)}
}
final class Payments {func peerStarsSubscriptionsContext(starsContext:Int?,missingBalance:Bool)->StarsSubscriptionsContext{StarsSubscriptionsContext()}}
final class Engine {let data=DataEngine();let payments=Payments()}
final class Context {let engine=Engine();var inAppPurchaseManager:ProductManager?=ProductManager()}
final class Pipe<T> {
 var values:[Subscriber<T,NoError>]=[];var removed=0
 var signal:Signal<T,NoError>{Signal{s in self.values.append(s);return ActionDisposable{self.removed+=1}}}
 func send(_ value:T){for s in values{s.putNext(value)}}
}
'''


def native_signal(source):
    parts=['import Foundation\n',MODELS]
    for name in ['Atomic.swift','Disposable.swift','Subscriber.swift']:
        parts.append((source/(SK+name)).read_text())
    signal=(source/(SK+'Signal.swift')).read_text();parts.append(signal[:signal.index('@available(iOS 13.0')])
    for name,markers in {
        'Signal_Mapping.swift':['public func map<T, E, R>(', 'private class DistinctUntilChangedContext', 'public func distinctUntilChanged<T: Equatable, E>('],
        'Signal_Meta.swift':['private final class SignalQueueState', 'public func switchToLatest<', 'public func mapToSignal<T, R, E>('],
    }.items():
        text=(source/(SK+name)).read_text();parts.extend(block(text,m) for m in markers)
    combine=(source/(SK+'Signal_Combine.swift')).read_text()
    for marker in ['private struct SignalCombineState', 'private func combineLatestAny<', 'private func signalOfAny<', 'public func combineLatest<T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, E>(']:
        parts.append(block(combine,marker))
    return '\n'.join(parts)


def selection(source):
    context=(source/CONTEXT).read_text()
    closure=block(context,'                |> mapToSignal { suggestions, dismissedSuggestions,')
    # This is the unchanged native priority tree with the two new filters; the
    # real ten-input combineLatest and switchToLatest execute below it.
    body=closure[closure.index(' in\n')+4:-1]
    signature=r'''
func choose(context:Context,suggestions:[ServerProvidedSuggestion],dismissedSuggestions:[String]=[],needsPasswordSetup:Bool?=false,newSessionReviews:[NewSessionReview]=[],newBotConnectionReviews:[NewBotConnectionReview]=[],data:(EnginePeer?,TelegramBirthday?)=(EnginePeer(id:1),nil),birthdays:[Int:TelegramBirthday]=[:],starsSubscriptionsContext:StarsSubscriptionsContext?=nil,accountFreezeConfiguration:FrozenConfiguration=FrozenConfiguration(),hidden:Signal<Bool,NoError>)->Signal<ChatListNotice?,NoError> {
 let starsSubscriptionsContextPromise=StarsPromise()
 return combineLatest(Signal<[ServerProvidedSuggestion],NoError>.single(suggestions),Signal<[String],NoError>.single(dismissedSuggestions),Signal<Bool?,NoError>.single(needsPasswordSetup),Signal<[NewSessionReview],NoError>.single(newSessionReviews),Signal<[NewBotConnectionReview],NoError>.single(newBotConnectionReviews),Signal<(EnginePeer?,TelegramBirthday?),NoError>.single(data),Signal<[Int:TelegramBirthday],NoError>.single(birthdays),Signal<StarsSubscriptionsContext?,NoError>.single(starsSubscriptionsContext),Signal<FrozenConfiguration,NoError>.single(accountFreezeConfiguration),hidden)
 |> mapToSignal { suggestions, dismissedSuggestions, needsPasswordSetup, newSessionReviews, newBotConnectionReviews, data, birthdays, starsSubscriptionsContext, accountFreezeConfiguration, hidePremiumOffers -> Signal<ChatListNotice?,NoError> in
'''
    return '\n'.join([native_signal(source),CHECK,
        block((source/SUGGESTIONS).read_text(),'public enum ServerProvidedSuggestion:').replace('public ',''),
        block(context,'    public enum ChatListNotice:').replace('public ',''),
        block((source/TAB).read_text(),'public enum NagramiXPremiumOfferSettings {'),
        block(context,'private func nagramiXPremiumOffersHiddenSignal('),
        block(context,'private func nagramiXChatListSuggestions('),signature,body,'}\n}\n',SELECTION_TESTS])


SELECTION_TESTS=r'''
@main struct SelectionTests {static func main(){
 let c=Context()
 let offers:[ServerProvidedSuggestion]=[.upgradePremium,.annualPremium,.restorePremium,.xmasPremiumGift,.gracePremium]
 for offer in offers {
  var visible:ChatListNotice?
  let a=choose(context:c,suggestions:[offer],hidden:.single(true)).start(next:{visible=$0})
  check(visible==nil,"all five typed Premium promotions are hidden on first load");a.dispose()
  let b=choose(context:c,suggestions:[offer],hidden:.single(false)).start(next:{visible=$0})
  check(visible != nil,"OFF restores exact native Premium path");b.dispose()
 }
 var value:ChatListNotice?
 let birthday=choose(context:c,suggestions:[],birthdays:[1:TelegramBirthday()],hidden:.single(true)).start(next:{value=$0})
 check(value==nil && c.engine.data.fetches==0,"birthday gift banner is hidden without fetching its peers");birthday.dispose()
 let nativeBirthday=choose(context:c,suggestions:[],birthdays:[1:TelegramBirthday()],hidden:.single(false)).start(next:{value=$0})
 if case .birthdayPremiumGift? = value{check(true,"OFF keeps birthday gift banner")}else{check(false,"OFF keeps birthday gift banner")};nativeBirthday.dispose()
 for hidden in [false,true] {
  let h=Signal<Bool,NoError>.single(hidden)
  let login=choose(context:c,suggestions:offers,newSessionReviews:[NewSessionReview(id:9)],hidden:h).start(next:{value=$0})
  check(value == .reviewLogin(newSessionReview:NewSessionReview(id:9),totalCount:1),"login security review outranks all offers");login.dispose()
  let bot=choose(context:c,suggestions:offers,newBotConnectionReviews:[NewBotConnectionReview(botId:1)],hidden:h).start(next:{value=$0})
  check(value == .reviewBotConnection(newBotConnectionReview:NewBotConnectionReview(botId:1),botUsername:"user",totalCount:1),"bot connection security review is preserved");bot.dispose()
  let password=choose(context:c,suggestions:offers+[.setupPassword],needsPasswordSetup:true,hidden:h).start(next:{value=$0})
  check(value == .setupPassword,"password setup warning is preserved");password.dispose()
  let frozen=choose(context:c,suggestions:offers,accountFreezeConfiguration:FrozenConfiguration(freezeUntilDate:1),hidden:h).start(next:{value=$0})
  check(value == .accountFreeze,"account restriction warning is preserved");frozen.dispose()
  let stars=choose(context:c,suggestions:[.starsSubscriptionLowBalance]+offers,starsSubscriptionsContext:StarsSubscriptionsContext(),hidden:h).start(next:{value=$0})
  if case .starsSubscriptionLowBalance? = value{check(true,"Stars balance warning is preserved")}else{check(false,"Stars balance warning is preserved")};stars.dispose()
 }
 let fallback=choose(context:c,suggestions:[.upgradePremium,.setupBirthday],hidden:.single(true)).start(next:{value=$0})
 check(value == .setupBirthday,"hiding an offer allows the next unrelated notice to appear");fallback.dispose()
 let link=ServerProvidedSuggestion.link(id:"other",url:"https://example.org",title:"title",subtitle:"text")
 check(nagramiXChatListSuggestions([.upgradePremium,link,.annualPremium,.setupPassword,.gracePremium],hidePremiumOffers:true)==[link,.setupPassword],"unrelated suggestions retain payloads and order")
 let defaults=UserDefaults.standard;let key="nagramix.interface.hidePremiumOffers"
 let previous=defaults.object(forKey:key);defaults.removeObject(forKey:key)
 defer{if let previous{defaults.set(previous,forKey:key)}else{defaults.removeObject(forKey:key)}}
 var events:[Bool]=[]
 let observer=nagramiXPremiumOffersHiddenSignal().start(next:{events.append($0)})
 check(events==[true],"observer publishes cold default immediately")
 NagramiXPremiumOfferSettings.setHidden(false,in:defaults)
 NagramiXPremiumOfferSettings.setHidden(false,in:defaults)
 NagramiXPremiumOfferSettings.setHidden(true,in:defaults)
 check(events==[true,false,true],"live checkbox changes emit once without restart")
 observer.dispose();NagramiXPremiumOfferSettings.setHidden(false,in:defaults)
 check(events==[true,false,true],"disposed observer receives no further events")
 NagramiXPremiumOfferSettings.setHidden(true,in:defaults)
 let products=Pipe<[Product]>();let manager=ProductManager();manager.availableProducts=products.signal;c.inAppPurchaseManager=manager
 var changes:[ChatListNotice?]=[]
 let active=choose(context:c,suggestions:[.upgradePremium,.setupBirthday],hidden:nagramiXPremiumOffersHiddenSignal()).start(next:{changes.append($0)})
 check(changes.last! == .setupBirthday && products.values.isEmpty,"cold ON skips StoreKit offer subscription")
 NagramiXPremiumOfferSettings.setHidden(false,in:defaults)
 check(products.values.count==1,"OFF subscribes to native offer pricing")
 NagramiXPremiumOfferSettings.setHidden(true,in:defaults)
 check(products.removed==1 && changes.last! == .setupBirthday,"ON cancels pending offer and restores next notice")
 let count=changes.count;products.send([])
 check(changes.count==count,"late pricing callback cannot resurrect a hidden Premium banner")
 active.dispose()
 print("Premium production selection/SignalKit checks: \(checks)")
}}
'''
