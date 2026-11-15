"""Исполнять настоящий UIButton/Cell с записывающей границей UIKit."""
from pathlib import Path
from validate_quick_format import block
from round_editor_quality_runtime import clean

U='submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift'
M='submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift'
ROOT=Path(__file__).resolve().parents[1]


def fixture(source):
    text=(source/U).read_text()
    code=(ROOT/'scripts/tests/NagramiXRoundTitleBoundary.swift').read_text()+'\n'+clean((source/M).read_text())+'\n'
    for marker in ['func nagramiXRoundQualityTitle(', 'private struct NagramiXRoundSegmentOption', 'private func nagramiXRoundQualityUsesVerticalLayout(', 'private final class NagramiXRoundSegmentButton:', 'private final class NagramiXRoundSegmentCell:']:
        # Only ObjC selector dispatch is adapted; bodies/constraints stay actual.
        code+='\n'+block(text,marker).replace('@objc ','').replace('#selector(tapped)','"tapped"')+'\n'
    return code+PROBES+TESTS


PROBES=r'''
private extension NagramiXRoundSegmentButton {
 var fixtureName:UILabel{nameLabel}
 var fixtureDetail:UILabel{detailLabel}
 var fixtureCheck:UIImageView{checkView}
 var fixtureLabels:UIStackView{nameLabel.superview as! UIStackView}
 func fixtureTap(){tapped()}
}
private extension NagramiXRoundSegmentCell {
 var fixtureButtons:[NagramiXRoundSegmentButton]{buttons}
 var fixtureRow:UIStackView{row}
 var fixtureSeparators:[UIView]{separators}
}
private func has(_ first:Anchor,_ second:Anchor,_ constant:CGFloat)->Bool {
 NSLayoutConstraint.active.contains{$0.first==first && $0.second==second && $0.relation=="=" && $0.constant==constant}
}
'''

TESTS=r'''
@main private enum RoundTitleChecks {
 static func main(){
  var checks=0
  func check(_ value:Bool,_ message:String){if !value{print("FAIL: "+message);exit(96)};checks+=1}
  let strings=PresentationStrings()
  for font:CGFloat in [14,17,20,26,34] {
   for available:CGFloat in [280,320,350,390,430,768] {
    NSLayoutConstraint.active=[]
    let cell=NagramiXRoundSegmentCell(presentationData:PresentationData(font),count:3,qualityLayout:true)
    let options=NagramiXRoundVideoSettings.Quality.allCases.map { q in NagramiXRoundSegmentOption(title:nagramiXRoundQualityTitle(q,strings:strings),subtitle:"\(q.rawValue)×\(q.rawValue)",selected:q == .maximum,enabled:true) }
    cell.contentView.frame.size.width=available
    cell.update(options,availableWidth:available)
    let minimum=cell.fixtureButtons.map{$0.minimumUnwrappedWidth}.max()!
    let vertical=cell.fixtureRow.axis == .vertical
    let column=vertical ? available-8:(available-10)/3
    check(vertical == (available-8 < minimum*3+2),"narrow widths reflow before clipping")
    check(cell.fixtureRow.distribution == .fillEqually,"quality columns retain equal widths")
    check(has(cell.fixtureRow.leadingAnchor,cell.contentView.leadingAnchor,4) && has(cell.fixtureRow.trailingAnchor,cell.contentView.trailingAnchor,-4),"axis decision uses actual row insets")
    for (index,button) in cell.fixtureButtons.enumerated() {
     let name=button.fixtureName,detail=button.fixtureDetail,mark=button.fixtureCheck,labels=button.fixtureLabels
     check(name.numberOfLines==1 && detail.numberOfLines==1,"quality names and resolutions never wrap")
     check(name.font==font && detail.font==floor(font*13/17),"quality preserves original font sizes")
     check(has(labels.trailingAnchor,button.trailingAnchor,-8),"quality title uses full width")
     check(!has(labels.trailingAnchor,mark.leadingAnchor,-4),"check no longer consumes title width")
     check(has(mark.leadingAnchor,detail.trailingAnchor,4) && has(mark.centerYAnchor,detail.centerYAnchor,0),"check belongs to resolution row")
     check(labels.alignment == .center,"quality names and resolutions remain centered")
     check(column-16>=name.intrinsicContentSize.width,"full quality word fits without font reduction")
     check((column-detail.intrinsicContentSize.width)/2-20>=4,"resolution check stays within segment")
     check(name.text==options[index].title && detail.text==options[index].subtitle,"names/resolutions retain their complete localized values")
     check(button.accessibilityLabel==options[index].title && button.accessibilityValue==options[index].subtitle,"VoiceOver keeps full title and resolution")
     var pressed=0;button.pressed={pressed+=1};button.fixtureTap()
     check(pressed==1,"quality tap still reaches original callback")
     button.update(NagramiXRoundSegmentOption(title:options[index].title,subtitle:options[index].subtitle,selected:false,enabled:false));button.fixtureTap()
     check(pressed==1 && !button.isEnabled && button.alpha==0.4,"disabled quality still rejects taps")
    }
    check(cell.fixtureButtons[2].fixtureName.text=="Максимум","Maximum stays one complete word")
    check(cell.fixtureSeparators.allSatisfy{$0.isHidden==vertical},"fallback hides horizontal-group separators")
    let fitted=cell.systemLayoutSizeFitting(CGSize(width:768,height:50),withHorizontalFittingPriority:.required,verticalFittingPriority:.required)
    check(fitted.width==768 && cell.fittings==1 && cell.fixtureRow.axis == .horizontal,"sizing hook recalculates orientation")
    cell.contentView.frame.size.width=280;cell.layoutSubviews()
    check((cell.fixtureRow.axis == .vertical)==nagramiXRoundQualityUsesVerticalLayout(availableWidth:280,minimumOptionWidth:minimum,count:3),"layout hook responds to actual content width")
   }
  }
  for subtitle:String? in [nil,"Стандартное сжатие"] {
   NSLayoutConstraint.active=[]
   let cell=NagramiXRoundSegmentCell(presentationData:PresentationData(),count:2)
   let values=[NagramiXRoundSegmentOption(title:"H.264 (AVC)",subtitle:subtitle,selected:true,enabled:true),NagramiXRoundSegmentOption(title:"H.265 (HEVC)",subtitle:subtitle,selected:false,enabled:true)]
   cell.update(values,availableWidth:100)
   check(cell.fixtureRow.axis == .horizontal,"other setting groups retain original horizontal layout")
   for button in cell.fixtureButtons {
    check(button.fixtureName.numberOfLines==0 && button.fixtureDetail.numberOfLines==0,"other groups retain multiline labels")
    check(has(button.fixtureLabels.trailingAnchor,button.fixtureCheck.leadingAnchor,-4) && has(button.fixtureCheck.centerYAnchor,button.centerYAnchor,0),"other groups retain original check constraints")
   }
  }
  print("PASS round quality title checks: \(checks)")
 }
}
'''
