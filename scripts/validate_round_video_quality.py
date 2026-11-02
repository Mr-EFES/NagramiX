#!/usr/bin/env python3
"""Проверки модели, export snapshot и атомарности позднего этапа кружков."""
import argparse,hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',required=True);a=p.parse_args()
 plan=json.loads((ROOT/'ios/round_video_quality_patches.json').read_text())
 spec=importlib.util.spec_from_file_location('round_quality',ROOT/'ios/round_video_quality.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with tempfile.TemporaryDirectory() as folder:
  t=Path(folder);native=t/'native'
  def seed():
   for n in plan['copies']:
    if (native/n).exists():(native/n).unlink()
   for n in set(plan['inputs'])|set(plan['guards']):
    f=native/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((a.source/n).read_bytes())
  def snap():return {str(f.relative_to(native)):hashlib.sha256(f.read_bytes()).hexdigest() for f in native.rglob('*') if f.is_file()}
  failures=0
  def reject(overlay):
   nonlocal failures
   before=snap()
   try:m.apply_round_video_quality(native,overlay)
   except SystemExit:pass
   else:raise AssertionError('invalid stage accepted')
   assert before==snap();failures+=1
  seed();m.apply_round_video_quality(native,ROOT/'ios')
  for n,h in plan['outputs'].items():assert hashlib.sha256((native/n).read_bytes()).hexdigest()==h
  for n in plan['inputs']:
   restored=(a.source/n).read_text()
   for path,old,new,count in plan['patches']:
    if path==n:assert restored.count(old)==count;restored=restored.replace(old,new,count)
   assert restored==(native/n).read_text()
  subprocess.run([a.swiftc,'-frontend','-parse',*[str(native/n) for n in list(plan['inputs'])+list(plan['copies']) if n.endswith('.swift')]],check=True)
  values=(native/'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift').read_text()
  # The exact production export override runs against AVFoundation dictionary boundaries.
  branch=values.split('    // Snapshot from this recording, including deferred resource conversion.\n',1)[1].split('    let compressionProperties: [String: Any]',1)[0]
  keys=['AVVideoAverageBitRateKey','AVVideoProfileLevelKey','AVVideoProfileLevelH264HighAutoLevel','AVVideoH264EntropyModeKey','AVVideoH264EntropyModeCABAC','AVVideoCodecKey','AVVideoWidthKey','AVVideoHeightKey','AVVideoCompressionPropertiesKey','AVFormatIDKey','kAudioFormatMPEG4AAC','AVSampleRateKey','AVEncoderBitRateKey','AVNumberOfChannelsKey']
  boundary='import Foundation\n'+''.join(f'let {key}="{key}"\n' for key in keys)+'''
enum Preset { case videoMessage, story }
struct MediaEditorValues { var qualityPreset:Preset?; var nagramiXRoundTuning:[Int]? }
enum AVVideoCodecType { static let h264="h264",hevc="hevc" }
enum MediaEditorVideoExport { struct Configuration {
 var videoSettings:[String:Any];var audioSettings:[String:Any];var values:MediaEditorValues;var frameRate:Float;var preferredDuration:Double?
} }
func export(_ values:MediaEditorValues)->MediaEditorVideoExport.Configuration? {
'''+branch+'''return nil
}
@main struct ExportTest {static func main() {
 for side in [480,512,640] {for fps in [30,60] {for codec in [0,1] {
  let c=export(.init(qualityPreset:.videoMessage,nagramiXRoundTuning:[side,fps,codec]))!
  precondition(c.videoSettings[AVVideoWidthKey] as? Int == side && c.videoSettings[AVVideoHeightKey] as? Int == side)
  precondition(c.frameRate == Float(fps))
  precondition(c.videoSettings[AVVideoCodecKey] as? String == (codec == 0 ? "h264":"hevc"))
  let compression=c.videoSettings[AVVideoCompressionPropertiesKey] as! [String:Any]
  precondition(compression[AVVideoAverageBitRateKey] as? Int == (side == 480 ? 1200000 : (side == 512 ? 1400000:1500000)))
  precondition((compression[AVVideoH264EntropyModeKey] != nil) == (codec == 0))
 }}}
 for bad:[Int] in [[],[640],[999,60,0],[640,0,0],[640,60,9]] {precondition(export(.init(qualityPreset:.videoMessage,nagramiXRoundTuning:bad)) == nil)}
 precondition(export(.init(qualityPreset:.story,nagramiXRoundTuning:[640,60,1])) == nil)
 precondition(export(.init(qualityPreset:.videoMessage,nagramiXRoundTuning:nil)) == nil)
 print("PASS: actual export override, 12 combinations, invalid/stock/stories unchanged")
} }
'''
  swift=t/'Export.swift';swift.write_text(boundary)
  for mode in [[],['-O']]:
   for label,files in [('settings',[ROOT/'ios/round_video_quality/Settings.swift',ROOT/'scripts/tests/NagramiXRoundVideoSettingsTests.swift']),('export',[swift])]:
    exe=t/(label+('opt' if mode else 'debug'))
    subprocess.run([a.swiftc,'-parse-as-library','-module-cache-path',str(t/'cache'),*mode,*map(str,files),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
  reject(ROOT/'ios')
  for name in plan['inputs']:
   seed();(native/name).write_bytes((native/name).read_bytes()+b'\n');reject(ROOT/'ios')
  seed();name=next(iter(plan['copies']));(native/name).parent.mkdir(parents=True,exist_ok=True);(native/name).write_text('collision');reject(ROOT/'ios')
  overlay=t/'overlay';overlay.mkdir()
  seed();bad=json.loads(json.dumps(plan));bad['outputs'][next(iter(bad['outputs']))]='0'*64
  (overlay/'round_video_quality_patches.json').write_text(json.dumps(bad));reject(overlay)
  print(f'PASS: all native Swift parse, exact replay, {failures} atomic fail-closed cases')
if __name__=='__main__':main()
