"""Полная production проверка праздников и независимое сравнение Calendar API."""
import snowfall_holidays_runtime as holidays


def fixture(source):
    text=holidays.fixture(source)
    oracle='''
private func verifyCalendarCompatibility() {
 let zone=TimeZone(identifier:"Asia/Shanghai")!
 var chinese=Calendar(identifier:.chinese);chinese.timeZone=zone
 var gregorian=Calendar(identifier:.gregorian);gregorian.timeZone=zone
 var count=0
 for year in 2020...2035 {for number in 1...366 {
  let date=gregorian.date(from:DateComponents(year:year,month:1,day:number,hour:12))!
  let modern=chinese.dateComponents([.month,.day,.isLeapMonth],from:date)
  let legacy=chinese.dateComponents(in:zone,from:date)
  if modern.month != legacy.month || modern.day != legacy.day || modern.isLeapMonth != legacy.isLeapMonth {
   print("Calendar regression: legacy components preserve month/day/leap flag");exit(96)
  }
  count+=1
 }}
 let leap=gregorian.date(from:DateComponents(year:2023,month:3,day:22,hour:12))!
 let components=chinese.dateComponents(in:zone,from:leap)
 if components.month != 2 || components.day != 1 || components.isLeapMonth != true {
  print("Calendar regression: leap month remains distinct");exit(96)
 }
 print("Calendar API compatibility: \\(count+1) checks passed")
}
'''
    marker='@main struct HolidaySnowTests {'
    assert text.count(marker)==1
    text=text.replace(marker,oracle+'\n'+marker,1)
    marker=' static func main(){\n'
    assert text.count(marker)==1
    return text.replace(marker,marker+'  verifyCalendarCompatibility()\n',1)


negatives=holidays.negatives
