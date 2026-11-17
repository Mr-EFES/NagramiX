"""Исполнить профиль вложения/выбор и NV12 canvas с явными UI/AV IO-hosts."""
import json,re
from pathlib import Path
from validate_quick_format import block
import round_editor_quality_runtime as old
from validate_app_language_localization import strings
ROOT=Path(__file__).resolve().parents[1]
E='submodules/TelegramUI/Components/ChatMediaEditorScreen/Sources/'
V=E+'ChatMediaEditorScreenVideo.swift';S=E+'ChatMediaEditorScreen.swift';G=E+'ChatMediaEditorScreenGallery.swift';Q=E+'ChatMediaEditorScreenQuality.swift';H=E+'NagramiXRoundQualitySheet.swift'
R='submodules/TelegramUI/Components/MediaEditor/Sources/NagramiXRoundVideoExport.swift'
X='submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorVideoExport.swift'


def model_fixture(source):
    code=old.fixture(source).split('@main struct RoundQualityTests',1)[0].replace('exit(91)','exit(96)')
    code+='\n'+block((source/V).read_text(),'func chatMediaEditorRoundVideoTuning(')+'\n'
    for k in ['AVVideoExpectedSourceFrameRateKey','AVVideoMaxKeyFrameIntervalKey','AVVideoColorPropertiesKey']:
        if 'let '+k+'=' not in code:code+='let '+k+'="'+k+'"\n'
    catalog=json.loads((ROOT/'ios/app_language_localization/ui_catalog.json').read_text())
    # Final translations were not changed by107. Use the exact guarded103 RU
    # resource when this early projection contains Swift sources only.
    path=source/'submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings'
    if not path.exists():
        from validate_upstream_13_2_release import checked_plan,OVERLAY
        plan=checked_plan('tab_visibility_sync');path=OVERLAY/plan['replacements']['submodules/NagramiXCore/Resources/ru.lproj/Localizable.strings']
    values=strings(path)
    labels={k:values[v['key']] for k,v in catalog.items() if v['key'] in values}
    code+='\nlet actualCatalog='+json.dumps(json.dumps(values,ensure_ascii=False),ensure_ascii=False)+'''.data(using:.utf8)!
let actualLabels='''+json.dumps(json.dumps(labels,ensure_ascii=False),ensure_ascii=False)+'''.data(using:.utf8)!
let catalog=try! JSONDecoder().decode([String:String].self,from:actualCatalog)
let labels=try! JSONDecoder().decode([String:String].self,from:actualLabels)
struct PresentationStrings {
 struct Primary{let languageCode="ru"};let primaryComponent=Primary()
 let UserInfo_NotificationsDefault="Default",nagramiXOptionSheetClose="Close",Common_Back="Back",Appearance_TextSize_Apply="Apply"
 func nagramiXLocalized(_ key:String)->String{catalog[key] ?? key}
 func nagramiXUILocalized(_ text:String)->String {
  if text.hasSuffix(" кадров/с"){return text};return labels[text] ?? text
 }
}
struct PresentationData {let strings=PresentationStrings()}
protocol ActionSheetItem {}
struct ActionSheetItemGroup {let items:[ActionSheetItem]}
final class ActionSheetController {
 var groups:[ActionSheetItemGroup]=[];var dismissed:((Bool)->Void)?;var closes=0
 init(presentationData:PresentationData){}
 func setItemGroups(_ value:[ActionSheetItemGroup]){groups=value}
 func dismissAnimated(){closes+=1;dismissed?(true)}
}
'''
    text=(source/H).read_text()
    code+='\n'+block(text,'struct NagramiXRoundQualityRow:')+'\n'+block(text,'func nagramiXRoundQualityRows(')+'\n'
    code+=block(text,'private final class NagramiXRoundQualitySelection').replace('private ','fileprivate ')+'\n'
    item=block(text,'private final class NagramiXRoundQualitySheetItem:');item=item.split('    func node(',1)[0]+'}\n'
    code+=item.replace('private ','fileprivate ')+'\n'+block(text,'func nagramiXRoundQualitySheet(')+'\n'
    code+=old.clean(block((source/Q).read_text(),'public func chatMediaEditorVideoQualityIsEnabled('))+'\n'
    return code+(ROOT/'scripts/tests/NagramiXGalleryRoundProfileTests.swift').read_text()


def reader_fixture(source):
    code=(ROOT/'scripts/tests/NagramiXGalleryRoundReaderBoundary.swift').read_text()
    text=(source/R).read_text()
    code+='\n'+block(text,'final class NagramiXRoundVideoFrameReader')+'\n'
    export=(source/X).read_text()
    code+='''
enum ReaderStatus {case reading,completed,failed}
final class ReaderHost {var status=ReaderStatus.reading;let timeRange=CMTimeRange(start:.zero,duration:CMTime(0.3))}
struct ConfigurationHost {var nagramiXIsCustomRoundVideo=true;let frameRate:Float=60}
struct WriterHost {func markVideoAsFinished(){}}
final class ExportHost {
 var configuration=ConfigurationHost()
 var reader:ReaderHost?=ReaderHost()
 var nagramiXRoundSampleReader:NagramiXRoundVideoFrameReader?
 var nagramiXRoundSamplingFailed=false
 let output:AVAssetReaderOutput
 var last:CMSampleBuffer?
 init(){output=AVAssetReaderOutput([CMSampleBuffer(0,0),CMSampleBuffer(0.1,1),CMSampleBuffer(0.2,2)]);let reader=self.reader!;output.onEOF={reader.status = .completed}}
'''+block(export,'    private func nagramiXCopyNextVideoSampleBuffer(')+'''
 func step()->Bool {let writer=WriterHost()
'''+block(export,'            if let reader = self.reader, reader.status != .reading &&')+'''
  last=nagramiXCopyNextVideoSampleBuffer(output);return last != nil
 }
}
'''
    return code+(ROOT/'scripts/tests/NagramiXGalleryRoundReaderTests.swift').read_text()
