"""Real holiday/settings/scheduler/view and native SignalKit; only OS edges adapted."""
from validate_quick_format import block
from snowfall_runtime import SETTINGS, VIEW, UI, BOUNDARY, ENTRY

POLICY='submodules/NagramiXCore/Sources/NagramiXSnowHolidays.swift'
SCHEDULE='submodules/NagramiXCore/Sources/NagramiXSnowSchedule.swift'
SK='submodules/SSignalKit/SwiftSignalKit/Source/'
NATIVE=['Atomic.swift','Disposable.swift','Subscriber.swift','Signal.swift','Signal_Mapping.swift','Signal_Combine.swift']


def fixture(source):
    parts=['import Foundation\n'+BOUNDARY.replace('static let willResignActiveNotification=', 'static let significantTimeChangeNotification=Notification.Name("significant");static let willResignActiveNotification=')]
    parts.append('public final class Queue {}\npublic func deliverOn<T,E>(_ queue:Queue)->(Signal<T,E>)->Signal<T,E>{{ $0 }}')
    for name in NATIVE[:3]:parts.append((source/(SK+name)).read_text())
    signal=(source/(SK+'Signal.swift')).read_text();parts.append(signal[:signal.index('@available(iOS 13.0')])
    for name,markers in {
        'Signal_Mapping.swift':['private class DistinctUntilChangedContext', 'public func distinctUntilChanged<T: Equatable, E>('],
        'Signal_Combine.swift':['private struct SignalCombineState', 'private func combineLatestAny<', 'private func signalOfAny<', 'public func combineLatest<T1, T2, T3, T4, T5, E>('],
    }.items():
        text=(source/(SK+name)).read_text();parts.extend(block(text,m) for m in markers)
    # Replace only the wall-clock/time-zone edge, leaving the entire production
    # settings implementation intact. Full unmodified helpers also emit a module.
    settings=(source/SETTINGS).read_text()
    assert settings.count('at: Date(), timeZone: .autoupdatingCurrent')==2
    settings=settings.replace('at: Date(), timeZone: .autoupdatingCurrent','at: clock, timeZone: clockZone')
    parts.extend([settings,(source/POLICY).read_text(),(source/SCHEDULE).read_text().replace('import UIKit\n',''),(source/VIEW).read_text().replace('import UIKit\n',''),ENTRY])
    ui=(source/UI).read_text()
    parts.extend([block(ui,'private func nagramiXSnowSettingsSignal('),block(ui,'private func nagramiXSnowEntries('),TESTS])
    return '\n'.join(parts)


def negatives(code):
    for name,old,new,label in [
        ('no-dec31','month == 12 && number == 31','month == 12 && number == 30','fixed holiday identified'),
        ('no-jan13','number == 13 || number == 14','number == 12 || number == 14','fixed holiday identified'),
        ('wrong-density','result.density = 75','result.density = 100','holiday forces density75'),
        ('master-not-forced','result.enabled = true','result.enabled = manual.enabled','holiday forces enabled'),
        ('cny-omitted','lunar.month == 1 && lunar.day == 1','lunar.month == 2 && lunar.day == 1','Chinese New Year follows changing civil dates'),
        ('missing-live-notify','if changed { NotificationCenter.default.post','if false && changed { NotificationCenter.default.post','open UI and emitters follow automatic change'),
        ('no-resume','if note.name == UIApplication.didBecomeActiveNotification { self.active = true }','if note.name == UIApplication.didBecomeActiveNotification { self.active = false }','foreground re-arms midnight timer'),
    ]:
        assert code.count(old)==1,(name,code.count(old));yield name,code.replace(old,new,1),label


TESTS=r'''
var clock=Date(timeIntervalSince1970:0)
var clockZone=TimeZone(identifier:"UTC")!
func date(_ y:Int,_ m:Int,_ d:Int,_ hour:Int=0,_ zone:TimeZone=clockZone)->Date {
 var c=Calendar(identifier:.gregorian);c.timeZone=zone
 return c.date(from:DateComponents(year:y,month:m,day:d,hour:hour))!
}
@main struct HolidaySnowTests {
 static func main(){
  let key="nagramix.atmosphere.snowfall",defaults=UserDefaults.standard,old=UserDefaults.standard.object(forKey:"nagramix.atmosphere.snowfall")
  defaults.removeObject(forKey:key);defer {defaults.set(old,forKey:key)}
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){FileHandle.standardError.write(Data(("Holiday snow regression: "+why+"\n").utf8));exit(96)};checks+=1}
  typealias H=NagramiXSnowHolidays
  let zones=["UTC","Europe/Moscow","America/Los_Angeles","Pacific/Kiritimati","America/Adak","Asia/Shanghai","Asia/Kolkata","Australia/Sydney"].map{TimeZone(identifier:$0)!}
  let chinese=[(2023,1,22),(2024,2,10),(2025,1,29),(2026,2,17),(2027,2,6),(2028,1,26),(2029,2,13),(2030,2,3),(2031,1,23),(2032,2,11),(2033,1,31),(2034,2,19)]
  for zone in zones {
   for (year,month,day) in chinese {
    let first=date(year,month,day,0,zone),end=date(year,month,day+1,0,zone)
    for t in [first,first.addingTimeInterval(0.01),date(year,month,day,12,zone),end.addingTimeInterval(-0.01)] {
     let window=H.window(at:t,timeZone:zone)
     check(window?.kind == .chineseNewYear && window?.start==first && window?.end==end,"Chinese New Year follows changing civil dates")
    }
    check(H.window(at:first.addingTimeInterval(-0.01),timeZone:zone)==nil && H.window(at:end,timeZone:zone)==nil,"Chinese holiday ends after one local day")
    for (m,d,kind) in [(12,25,H.Kind.christmas),(1,7,.orthodoxChristmas),(12,31,.newYear),(1,1,.newYear),(1,13,.oldNewYear),(1,14,.oldNewYear)] {
     let t=date(year,m,d,12,zone),w=H.window(at:t,timeZone:zone)
     check(w?.kind==kind,"fixed holiday identified")
     check(w!.start<=t && t<w!.end,"half open holiday interval")
    }
    let newStart=date(year,12,31,0,zone),newEnd=date(year+1,1,2,0,zone)
    check(H.window(at:newStart,timeZone:zone)?.start==newStart,"new year includes December 31")
    check(H.window(at:newEnd.addingTimeInterval(-0.01),timeZone:zone)?.end==newEnd,"new year includes all January 1")
    check(H.window(at:newStart.addingTimeInterval(-0.01),timeZone:zone)==nil && H.window(at:newEnd,timeZone:zone)==nil,"new year exact outer boundaries")
    let oldStart=date(year,1,13,0,zone),oldEnd=date(year,1,15,0,zone)
    check(H.window(at:oldStart,timeZone:zone)?.start==oldStart,"old new year includes January 13")
    check(H.window(at:oldEnd.addingTimeInterval(-0.01),timeZone:zone)?.end==oldEnd,"old new year includes all January 14")
    check(H.window(at:oldStart.addingTimeInterval(-0.01),timeZone:zone)==nil && H.window(at:oldEnd,timeZone:zone)==nil,"old new year exact outer boundaries")
   }
  }
  // Enumerate whole years: only seven civil dates, with no extra lunar holidays.
  for (year,m,d) in chinese {
   var c=Calendar(identifier:.gregorian);c.timeZone=clockZone
   var day=date(year,1,1,12),total=0
   while c.component(.year,from:day)==year {
    let month=c.component(.month,from:day),number=c.component(.day,from:day)
    let expected=(month==12 && (number==25 || number==31)) || (month==1 && [1,7,13,14].contains(number)) || (month==m && number==d)
    check((H.window(at:day,timeZone:clockZone) != nil)==expected,"only requested calendar dates activate")
    if expected {total+=1};day=c.date(byAdding:.day,value:1,to:day)!
   }
   check(total==7,"seven requested civil days per year")
  }
  let la=TimeZone(identifier:"America/Los_Angeles")!
  check(H.dayInterval(at:date(2026,3,8,12,la),timeZone:la)!.duration==23*3600,"local midnight respects short DST day")
  check(H.dayInterval(at:date(2026,11,1,12,la),timeZone:la)!.duration==25*3600,"local midnight respects long DST day")
  check(H.window(at:Date(timeIntervalSinceReferenceDate:.infinity),timeZone:clockZone)==nil,"invalid calendar input fails closed")
  let holiday=H.window(at:date(2026,12,25),timeZone:clockZone)
  for enabled in [false,true] {for chats in [false,true] {for density in stride(from:10,through:100,by:5) {
   var manual=NagramiXSnowConfiguration();manual.enabled=enabled;manual.inChats=chats;manual.density=density
   let effective=H.configuration(manual,during:holiday)
   check(effective.enabled,"holiday forces enabled");check(effective.density==75,"holiday forces density75")
   check(effective.inChats==chats,"chat preference remains manual")
   check(H.configuration(manual,during:nil)==manual,"ordinary day restores all saved preferences")
  }}}
  clock=date(2026,12,24,12)
  check(!NagramiXSnowSettings.current.enabled,"ordinary cold start remains OFF")
  check(defaults.object(forKey:key)==nil,"calendar read never persists implicit ON")
  let parent=UIView(frame:CGRect(x:0,y:0,width:390,height:120));parent.window=UIWindow()
  let header=NagramiXSnowView(scope:.header);header.setVisible(true);header.bind(to:parent)
  let emitter=header.layer.children.first as! CAEmitterLayer
  var rows:[Int]=[]
  let disposable=combineLatest(Signal<Int,NoError>.single(1),Signal<Int,NoError>.single(2),Signal<Int,NoError>.single(3),Signal<Int,NoError>.single(4),nagramiXSnowSettingsSignal()).start(next:{_,_,_,_,v in rows.append(nagramiXSnowEntries(v).count)})
  check(rows==[2] && emitter.birthRate==0,"initial native signal has OFF rows and stopped emitter")
  final class Timers {var dates:[Date]=[];var actions:[()->Void]=[];var timers:[Timer]=[]
   func make(_ date:Date,_ action:@escaping()->Void)->Timer {dates.append(date);actions.append(action);let t=Timer(fire:date,interval:0,repeats:false){_ in action()};timers.append(t);return t}
  }
  let timers=Timers()
  var driver:NagramiXSnowSchedule?=NagramiXSnowSchedule(now:{clock},timeZone:{clockZone},makeTimer:timers.make)
  driver!.start();driver!.start()
  check(timers.dates==[date(2026,12,25)],"one idempotent local-midnight timer")
  clock=date(2026,12,25);timers.actions.last!()
  check(rows.last==4 && emitter.birthRate==1 && NagramiXSnowSettings.current.density==75,"open UI and emitters follow automatic change")
  check(defaults.object(forKey:key)==nil,"automatic activation does not write storage")
  let rate=emitter.emitterCells!.reduce(Float(0)){$0+$1.birthRate}
  check(abs(rate-13.5)<0.001,"holiday density reaches native emitter")
  NagramiXSnowSettings.update{$0.enabled=false;$0.density=20;$0.inChats=false}
  check(NagramiXSnowSettings.current.enabled && NagramiXSnowSettings.current.density==75,"manual OFF cannot defeat holiday")
  check(!NagramiXSnowSettings.read(in:defaults).enabled && NagramiXSnowSettings.read(in:defaults).density==20,"manual values saved without holiday overwrite")
  let count=rows.count
  NotificationCenter.default.post(name:.NSCalendarDayChanged,object:nil)
  check(rows.count==count,"duplicate schedule notification does not rebuild rows")
  deviceLowPower=true;NotificationCenter.default.post(name:.NSProcessInfoPowerStateDidChange,object:nil)
  check(emitter.birthRate==0,"holiday respects low power")
  deviceLowPower=false;UIAccessibility.isReduceMotionEnabled=true;NotificationCenter.default.post(name:UIAccessibility.reduceMotionStatusDidChangeNotification,object:nil)
  check(emitter.birthRate==0,"holiday respects reduced motion")
  UIAccessibility.isReduceMotionEnabled=false;NotificationCenter.default.post(name:UIAccessibility.reduceMotionStatusDidChangeNotification,object:nil)
  NotificationCenter.default.post(name:UIApplication.willResignActiveNotification,object:nil)
  check(timers.timers.allSatisfy{!$0.isValid} && emitter.birthRate==0,"inactive invalidates timers and stops emitter")
  clock=date(2026,12,26,10)
  NotificationCenter.default.post(name:UIApplication.didBecomeActiveNotification,object:nil)
  check(!NagramiXSnowSettings.current.enabled && NagramiXSnowSettings.current.density==20 && rows.last==2,"resume after holiday restores saved OFF")
  check(timers.dates.last==date(2026,12,27),"foreground re-arms midnight timer")
  NagramiXSnowSettings.update{$0.enabled=true;$0.density=40}
  clock=date(2026,12,31);NotificationCenter.default.post(name:UIApplication.significantTimeChangeNotification,object:nil)
  check(NagramiXSnowSettings.current.density==75,"clock jump enters holiday")
  clock=date(2027,1,1,23);NotificationCenter.default.post(name:.NSCalendarDayChanged,object:nil)
  check(NagramiXSnowSettings.current.density==75,"two full local New Year days")
  clock=date(2027,1,2);NotificationCenter.default.post(name:.NSCalendarDayChanged,object:nil)
  check(NagramiXSnowSettings.current.enabled && NagramiXSnowSettings.current.density==40,"manual ON survives holiday expiry")
  // Same instant, different phone date: timezone change must invalidate the cache.
  clock=date(2026,12,24,16);clockZone=TimeZone(identifier:"Asia/Tokyo")!
  NotificationCenter.default.post(name:.NSSystemTimeZoneDidChange,object:nil)
  check(NagramiXSnowSettings.current.density==75,"timezone change immediately enters local holiday")
  clockZone=TimeZone(identifier:"UTC")!;NotificationCenter.default.post(name:.NSSystemTimeZoneDidChange,object:nil)
  check(NagramiXSnowSettings.current.density==40,"timezone change immediately leaves local holiday")
  check(timers.timers.filter{$0.isValid}.count==1,"at most one live midnight timer")
  weak var weakDriver=driver;driver=nil
  check(weakDriver==nil && timers.timers.allSatisfy{!$0.isValid},"scheduler releases observers and timer")
  let frozen=rows.count;disposable.dispose();NagramiXSnowSettings.update{$0.enabled=false}
  check(rows.count==frozen,"disposed UI observer never receives further values")
  print("Holiday snowfall production checks: \(checks)")
 }
}
'''
