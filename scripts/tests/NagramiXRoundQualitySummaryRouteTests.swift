var checks=0
func check(_ condition:@autoclosure()->Bool,_ why:String){checks+=1;if !condition(){print("FAIL: "+why);exit(96)}}
@main struct RoundQualitySummaryRouteTests {
 static func main(){
  FixtureRoundSettings.value = .init(enabled:true,quality:.high,frameRate:.smooth,codec:.hevc,bitRate:1_600_000)
  let node=RouteHost();node.mediaEditor.values.nagramiXRoundTuning=[480,30,0,1_000_000]
  node.refreshToolbarValues()
  check(node.mediaEditor.values.nagramiXRoundTuning==[512,60,1,1_600_000],"actual toolbar resolves current settings before badge layout")
  node.qualityTabPressed()
  check(node.controller!.sheets.count==1 && node.normalQuality==0,"round fifth button opens summary and never ordinary quality slider")
  check(node.saves==1 && node.layouts==1 && node.mediaEditor.drawings==1,"actual click captures and saves one snapshot")
  check(node.mediaEditor.entityIds==[7] && node.mediaEditor.values.drawing=="drawing","actual capture keeps drawing and filters render-only entities")
  let rows=node.controller!.sheets[0].groups[0].items
  check(rows.count==6 && (rows[1] as! NagramiXRoundQualitySheetItem).value=="Высокое","presented summary matches captured settings")
  let frozen=node.mediaEditor.values
  FixtureRoundSettings.value = .init(enabled:false,quality:.maximum,frameRate:.smooth,codec:.hevc,bitRate:2_000_000)
  let captured=node.captureCurrentValues()
  check(captured.nagramiXRoundTuning==nil && node.mediaEditor.values.nagramiXRoundTuning==nil,"actual send capture removes custom tuning when feature OFF")
  check(frozen.nagramiXRoundTuning==[512,60,1,1_600_000],"previously prepared value stays frozen")
  node.qualityTabPressed()
  check(node.controller!.sheets[1].groups[0].items.count==2,"OFF click opens only native default summary")
  for state in 0..<7 {
   let guarded=RouteHost()
   switch state {case 0:guarded.activeTool = .quality;case 1:guarded.isSending=true;case 2:guarded.isInvalidated=true;case 3:guarded.controller!.isDismissing=true;case 4:guarded.validLayout=nil;case 5:guarded.canEndCaption=false;default:guarded.showsQualityTab=false}
   guarded.qualityTabPressed()
   check(guarded.controller!.sheets.isEmpty && guarded.saves==0 && guarded.mediaEditor.drawings==0,"busy/invalid/editor/hidden/caption guards reject popup without side effects")
  }
  let missing=RouteHost();missing.controller=nil;missing.qualityTabPressed();check(missing.saves==0,"missing controller is safe")
  let muted=RouteHost();muted.mediaEditor.values.videoIsMuted=true;muted.qualityTabPressed()
  check(muted.controller!.sheets.count==1,"muted round video still allows read-only summary")
  let ordinary=RouteHost();ordinary.mediaEditor.values.qualityPreset = .normal;ordinary.qualityTabPressed()
  check(ordinary.normalQuality==1 && ordinary.controller!.sheets.isEmpty,"ordinary video keeps native quality route")
  ordinary.mediaEditor.values.videoIsMuted=true;ordinary.qualityTabPressed();check(ordinary.normalQuality==1,"ordinary muted video keeps disabled quality route")
  let photo=RouteHost();photo.subject.isVideo=false;photo.qualityTabPressed()
  check(photo.captionModel!.toggles==1 && photo.photoTooltips==1 && photo.controller!.sheets.isEmpty,"photo quality route unchanged")
  check(!disabled(tab:.qualityTab,isVideo:true,roundVideoSelected:true,disabledTabs:[.qualityTab]),"round quality control enabled for inspection")
  check(disabled(tab:.qualityTab,isVideo:true,roundVideoSelected:false,disabledTabs:[.qualityTab]),"ordinary video disabled mask preserved")
  check(disabled(tab:.cropTab,isVideo:true,roundVideoSelected:true,disabledTabs:[.cropTab]),"unrelated disabled tabs preserved")
  print("Round quality actual click/capture/toolbar checks: \(checks)")
 }
}
