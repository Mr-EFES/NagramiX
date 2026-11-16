"""Photos chunks → whole exporter → actual gallery preparation → native video resource branch.

Photos/UIKit, model storage and encoder are explicit edges; original bytes use real files.
"""
from pathlib import Path
from validate_quick_format import block
import original_video_media_runtime as raw
import original_video_mode_runtime as mode
ROOT=Path(__file__).resolve().parents[1]
HELPER=mode.HELPER
LEGACY=mode.LEGACY
BASE=mode.BASE


def fixture(source):
    core,boundary,actual,_=raw.parts(source)
    boundary=boundary.replace('public struct PixelDimensions {','public struct PixelDimensions {\n    var cgSize:CGSize {CGSize(width:Int(width),height:Int(height))}\n    init(){self.init(width:96,height:64)}',1)
    boundary=boundary.replace('public struct TelegramMediaFile {','public final class TelegramMediaFile:EngineRawMedia {',1).replace('let partialReference: Int?; let resource: LocalFileMediaResource','let partialReference: Int?; let resource: Resource',1)
    marker='    // NATIVE_FILE_CLASSIFICATION'
    # raw.parts has already replaced the marker by real native getters.
    a=boundary.index('public final class TelegramMediaFile:');b=boundary.index('    public var isVideo:',a)
    init='''    init(fileId:EngineMedia.Id,partialReference:Int?,resource:Resource,previewRepresentations:[TelegramMediaImageRepresentation],videoThumbnails:[Int],videoCover:TelegramMediaImage?,immediateThumbnailData:Data?,mimeType:String,size:Int64?,attributes:[TelegramMediaFileAttribute],alternativeRepresentations:[Int]) {
 self.fileId=fileId;self.partialReference=partialReference;self.resource=resource;self.previewRepresentations=previewRepresentations;self.videoThumbnails=videoThumbnails;self.videoCover=videoCover;self.immediateThumbnailData=immediateThumbnailData;self.mimeType=mimeType;self.size=size;self.attributes=attributes;self.alternativeRepresentations=alternativeRepresentations
 }
'''
    boundary=boundary[:b]+init+boundary[b:]
    old_asset=block(boundary,'public final class PHAsset {')
    asset=old_asset.replace('    var mediaType','    static var registry:[String:PHAsset]=[:]\n    static func fetchAssets(withLocalIdentifiers ids:[String],options:Int?)->AssetResult {AssetResult(ids.first.flatMap{registry[$0]})}\n    var mediaSubtypes:AssetSubtypes=[]\n    var mediaType',1)
    boundary=boundary.replace(old_asset,asset,1)
    manager=block(boundary,'final class PHAssetResourceManager {')
    boundary=boundary.replace(manager,(ROOT/'scripts/tests/NagramiXOriginalGalleryResourceBoundary.swift').read_text(),1)
    parts=[mode.GEOMETRY_IMPORTS,core,'protocol EngineRawMedia {}\nextension TelegramMediaImage:EngineRawMedia {}\nstruct AssetSubtypes:OptionSet {let rawValue:Int;static let videoHighFrameRate=AssetSubtypes(rawValue:1)}\nfinal class AssetResult {let firstObject:PHAsset?;init(_ v:PHAsset?){firstObject=v}}',boundary]
    for marker in ['enum MediaCropOrientation {','struct Perspective {','enum MediaQualityPreset {','struct MediaEditorValues {','struct ChatMediaSendConvertedGif {','struct ChatMediaSendPreparedLivePhoto {','struct ChatMediaSendPreparedAnimatedPhoto {','enum ChatMediaSendLivePhotoMode {']:
        parts.append(block(mode.BOUNDARY,marker))
    parts.append((ROOT/'scripts/tests/NagramiXOriginalGalleryRoutingBoundary.swift').read_text())
    for marker in ['public struct ChatMediaSendItemOptions:','public struct ChatMediaSendGlobalOptions:']:
        parts.append(block((source/(BASE+'Sources/ChatMediaSendPlan.swift')).read_text(),marker).replace('public ',''))
    parts.append('\n'.join(l for l in (source/(BASE+'Sources/ChatMediaSendItem.swift')).read_text().splitlines() if not l.startswith('import ')).replace('public ',''))
    parts.append(block((source/(BASE+'Sources/ChatMediaEditorItemStore.swift')).read_text(),'public func chatMediaEditorValuesHaveVisualEdits(').replace('public ',''))
    parts.append((ROOT/'scripts/tests/NagramiXOriginalGalleryLegacyBoundary.swift').read_text())
    legacy=(source/LEGACY).read_text()
    for marker in ['private enum LegacyAssetVideoData {','private enum LegacyAssetItem {','private final class LegacyAssetItemWrapper: NSObject {']:
        parts.append(block(legacy,marker))
    parts.append(actual)
    parts.append(block(legacy,'private func nagramiXPrepareOriginalVideoValue('))
    parts.append('\n'.join(l for l in (source/HELPER).read_text().splitlines() if not l.startswith('import ')))
    stock=(source/(BASE+'Sources/ChatMediaSendMessages.swift')).read_text()
    branch=block(stock,'        if isVideo {')
    a=stock.index('    case let .prebuilt(media):');b=stock.index('\n    }',a);prebuilt=stock[a:b]
    parts.append('''func routedMedia(_ item:ChatMediaSendItem)->(media:EngineRawMedia,stickerFiles:[TelegramMediaFile])? {
 let storeResourceData:(EngineMediaResource.Id,Data)->Void={_,_ in}
 switch item.source {
 case let .libraryAsset(identifier,pixelSize,isVideo,duration):
'''+branch+'''
 return nil
'''+prebuilt+'''
 default:return nil
 }
}
''')
    render=(source/mode.RENDER).read_text()
    parts.append(block(render,'func nagramiXPhotoSendOptions('))
    parts.append(block(render,'public func chatMediaSendMessages(context:').replace('public ',''))
    data=(raw.FIXTURES/'manifest.json').read_text()
    import json,base64,hashlib
    payload={}
    for n,h in json.loads(data)['files'].items():
        blob=(raw.FIXTURES/n).read_bytes();assert hashlib.sha256(blob).hexdigest()==h;payload[n]=base64.b64encode(blob).decode()
    extras=ROOT/'scripts/tests/fixtures/original-video-gallery'
    for n,item in json.loads((extras/'manifest.json').read_text())['files'].items():
        blob=(extras/n).read_bytes();assert hashlib.sha256(blob).hexdigest()==item['sha256'];payload[n]=base64.b64encode(blob).decode()
    tests=(ROOT/'scripts/tests/NagramiXOriginalGalleryTests.swift').read_text()
    for token,n in [('SYNTHETIC_MP4_BASE64','video.mp4'),('SYNTHETIC_MOV_BASE64','video.mov'),('H264_60_BASE64','h264-60.mp4'),('HEVC_60_BASE64','hevc-60.mov')]:tests=tests.replace(token,payload[n])
    parts.append(tests)
    return '\n'.join(parts)
