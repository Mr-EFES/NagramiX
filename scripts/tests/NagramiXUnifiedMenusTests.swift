@main struct UnifiedMenusTests {
 static func main(){
  var checks=0
  func check(_ value:@autoclosure()->Bool,_ why:String){if !value(){print("FAIL: "+why);exit(96)};checks+=1}
  func rows(_ sheet:ActionSheetController)->[NagramiXOptionSheetItem]{sheet.groups[0].items.compactMap{$0 as? NagramiXOptionSheetItem}}
  openDownloads();let download=presented!;let downloadRows=rows(download)
  check(downloadRows.count==3,"download contains exactly header and two options without footer")
  check(downloadRows[1].title=="Среднее" && downloadRows[1].subtitle=="Умеренная нагрузка на сеть" && downloadRows[2].title=="Максимум" && downloadRows[2].subtitle=="Повышенная нагрузка на сеть","two download choices retain exact titles and descriptions")
  for mode in NagramiXDownloadAcceleration.allCases {
   NagramiXTabSettings.current.downloads.mode=mode;openDownloads();let sheet=presented!;let items=rows(sheet)
   let expected=mode == .maximum ? 2:1
   for i in 1...2 {if case let .option(selected,_)=items[i].kind{check(selected==(i==expected),"download saved and legacy modes show exactly one selected radio")}}
   items[2].action();items[1].action();check(NagramiXTabSettings.current.downloads.mode == .maximum && sheet.dismissals==1,"download choice commits and dismisses exactly once")
  }
  NagramiXTabSettings.current.downloads.enabled=true;openDownloads();NagramiXTabSettings.current.downloads.enabled=false;rows(presented!)[1].action();check(NagramiXTabSettings.current.downloads.mode == .maximum,"disabling downloads while open blocks stale write")
  for provider in NagramiXDnsProvider.allCases {
   NagramiXTabSettings.current.dnsProvider=provider;NagramiXTabSettings.current.customDohUrl="https://example.com/dns-query";openDns();let sheet=presented!;let items=rows(sheet)
   check(items.count==7 && items.allSatisfy{$0.floatingGlass} && !sheet.nagramiXBottomAttached,"DNS uses same floating style and preserves all six providers")
   for (i,p) in NagramiXDnsProvider.allCases.enumerated(){if case let .option(selected,_)=items[i+1].kind{check(selected==(p==provider),"DNS persisted noncontiguous IDs map to correct selected radio")}}
   items[0].action();items[1].action();check(NagramiXTabSettings.current.dnsProvider==provider && sheet.dismissals==1,"closing DNS never changes provider")
   openDns();rows(presented!)[1].action();check(NagramiXTabSettings.current.dnsProvider == .system,"DNS ordinary choice keeps existing settings callback")
  }
  NagramiXTabSettings.current.dnsProvider = .telegram;NagramiXTabSettings.current.customDohUrl="";openDns();let custom=rows(presented!).last!;check(custom.disclosure,"custom DoH has a disclosure accessory");custom.action();custom.action();check(editorOpens==1 && NagramiXTabSettings.current.dnsProvider == .telegram,"empty custom DoH opens existing editor once without premature provider write")
  NagramiXTabSettings.current.customDohUrl="https://example.com/dns-query";openDns();rows(presented!).last!.action();check(editorOpens==1 && NagramiXTabSettings.current.dnsProvider == .customDoh,"existing custom DoH keeps previous direct-selection behavior")
  for preset in NagramiXTypingPreset.allCases {
   NagramiXTypingSettings.current.enabled=true;NagramiXTypingSettings.current.preset=preset;openEffect();let sheet=presented!;let items=rows(sheet)
   check(items.count==7 && items.allSatisfy{$0.floatingGlass} && !sheet.nagramiXBottomAttached,"all six typing effects use the shared floating style")
   items[preset.rawValue+1].action();items[1].action();check(NagramiXTypingSettings.current.preset==preset && sheet.dismissals==1,"typing effect selection preserves preset and writes once")
  }
  openEffect();let effect=presented!;NagramiXTypingSettings.current.enabled=false;rows(effect)[1].action();check(NagramiXTypingSettings.current.preset == .custom,"disabled typing effects block stale writes")
  for outside in [true,false] {
   var selected=0;let sheet=nagramiXOptionSheet(presentationData:PresentationData(),title:"Menu",options:[.init(id:1,title:"One",subtitle:"")],selectedId:1,footnote:"",floatingGlass:true,selected:{_ in selected+=1})
   if outside{sheet.dismissed?(true)}else{rows(sheet)[0].action()};rows(sheet)[1].action();check(selected==0,"close and outside dismissals block late selections")
  }
  let ordinary=NagramiXOptionSheetItem(kind:.option(selected:false,separator:false),title:"Unselected",floatingGlass:true)
  let ordinaryNode=ordinary.node(theme:ActionSheetControllerTheme()) as! NagramiXOptionSheetItemNode
  check(!ordinaryNode.checkView.isHidden && ordinaryNode.checkView.image?.symbol=="circle","unselected ordinary options display the outlined radio")
  ordinaryNode.button.highligthedChanged?(true);check(!ordinaryNode.selectionView.isHidden,"pressing an unselected row shows highlight feedback")
  ordinaryNode.button.highligthedChanged?(false);check(ordinaryNode.selectionView.isHidden,"releasing an unselected row restores plain material")
  let legacy=nagramiXOptionSheet(presentationData:PresentationData(),title:"Legacy",options:[.init(id:1,title:"One",subtitle:"")],selectedId:1,footnote:"Existing help",bottomAttached:true,selected:{_ in})
  check(legacy.nagramiXBottomAttached && rows(legacy).count==3 && rows(legacy).allSatisfy{!$0.floatingGlass},"unrelated callers retain existing defaults and footnotes")
  for glass in [false,true] {for rtl in [false,true] {for font:CGFloat in [15,17,23,30] {for width:CGFloat in [230,320,390,768] {
   let theme=ActionSheetControllerTheme(baseFontSize:font)
   var nodes:[ActionSheetItemNode]=[]
   for kind in [NagramiXOptionSheetItem.Kind.header(closeTitle:"Close"),.option(selected:false,separator:true),.option(selected:true,separator:false)] {
    let item=NagramiXOptionSheetItem(kind:kind,title:String(repeating:"Long title ",count:font>20 ? 4:1),subtitle:kind.isTestOption ? "Subtext": "",floatingGlass:glass,disclosure:kind.isTestOption)
    let node=item.node(theme:theme) as! NagramiXOptionSheetItemNode;node.view.effectiveUserInterfaceLayoutDirection=rtl ? .rightToLeft:.leftToRight
    let size=node.updateLayout(constrainedSize:CGSize(width:width,height:844),transition:.immediate)
    check(size.height>=44,"all menu rows and headers retain accessible touch height")
    check(node.titleLabel.frame.minX>=item.horizontalInset && node.titleLabel.frame.maxX<=width-item.horizontalInset,"long labels stay within horizontal padding")
    if case .header=kind {check(node.titleLabel.frame.intersection(node.closeButton.frame).isNull,"header wraps without colliding with close button");check(node.grabber.isHidden==glass,"floating headers hide the drag handle")}
    if case let .option(isSelected,_)=kind {
     check(node.checkView.isHidden == (glass ? !isSelected : !isSelected),"selected disclosure option remains visibly selected")
     check(node.selectionView.isHidden == (!glass || !isSelected),"selected background is opt-in only")
     if glass {check(node.backgroundNode.backgroundColor?.cgColor.alpha==0 && !node.disclosureView.isHidden,"glass rows expose shared material and custom disclosure")}
    }
    nodes.append(node)
   }
   let group=ActionSheetItemGroupNode(theme:theme);group.updateItemNodes(nodes);_ = group.updateLayout(constrainedSize:CGSize(width:width,height:600),transition:.immediate)
   check(group.nagramiXFloatingGlass==glass && group.clippingNode.cornerRadius == (glass ? 28:16),"native glass styling is opt-in and preserves default corners")
   let host=ActualInsetsHost();host.itemGroupsContainerNode.groupNodes=[group]
   check(host.nagramiXContainerInsets.left==(glass ? 16:10) && host.nagramiXContainerInsets.bottom==(glass ? 18:10),"floating menus share native safe margins without changing other sheets")
   host.allowInputInset=true;check(host.nagramiXContainerInsets.left==10,"keyboard-attached menus preserve default positioning")
  }}}}
  for available in [false,true] {for light in [false,true] {
   fixtureGlassAvailable=available
   let theme=ActionSheetControllerTheme(backgroundType:light ? .light:.dark)
   let group=ActionSheetItemGroupNode(theme:theme)
   let item=NagramiXOptionSheetItem(kind:.header(closeTitle:"Close"),title:"Header",floatingGlass:true)
   group.updateItemNodes([item.node(theme:theme)]);_ = group.updateLayout(constrainedSize:CGSize(width:350,height:500),transition:.immediate)
   check((group.backgroundEffectView.effect is UIGlassEffect)==available,"native glass and older blur fallback are both supported")
   check(group.backgroundEffectView.overrideUserInterfaceStyle==(light ? .light:.dark),"glass uses application theme rather than phone theme")
   group.updateItemNodes([ActionSheetItemNode(52)]);_ = group.updateLayout(constrainedSize:CGSize(width:350,height:500),transition:.immediate)
   check(group.clippingNode.cornerRadius==16 && group.clippingNode.layer.borderWidth==0,"reusing a group for native content restores original style")
  }}
  print("PASS \(checks) actual unified-menu factory/caller/node/native-group checks; UIKit/Texture metrics and presentation are explicit boundaries")
 }
}
extension NagramiXOptionSheetItem.Kind {var isTestOption:Bool{if case .option=self{return true};return false}}
