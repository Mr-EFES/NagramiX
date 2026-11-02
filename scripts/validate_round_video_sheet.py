#!/usr/bin/env python3
"""Проверка нижней панели кружков и подключения Cinematic без исполнения Apple API."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path);a=p.parse_args()
 from validate_round_video_bitrate import delegate_if_applied
 if delegate_if_applied(a): return
 v=json.loads((ROOT/'ios/round_video_sheet_patches.json').read_text())
 expected={**v['guards'],**v['outputs'],**{name:item['sha256'] for name,item in v['copies'].items()}}
 page_path=ROOT/'ios/round_video_page_patches.json'
 page=json.loads(page_path.read_text()) if page_path.exists() else None
 refinement=json.loads((ROOT/'ios/round_video_refinement_patches.json').read_text())
 refined=all(hashlib.sha256((a.source/name).read_bytes()).hexdigest()==sha for name,sha in refinement['outputs'].items())
 latest=page is not None and hashlib.sha256((a.source/'submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift').read_bytes()).hexdigest()==page['outputs']['submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift']
 if latest or refined:expected.update(page['outputs'])
 if refined:expected.update(refinement['outputs'])
 for name,sha in expected.items():assert hashlib.sha256((a.source/name).read_bytes()).hexdigest()==sha,name
 if refined:
  if a.swiftc:subprocess.run(['python3',str(ROOT/'scripts/validate_round_video_refinement.py'),'--source',str(a.source),'--swiftc',str(a.swiftc)],check=True)
  print('PASS: previous sheet/capture guards retained; refined page and capture presets checked')
  return
 template='round_video_page' if latest else 'round_video_sheet'
 if a.swiftc:
  with tempfile.TemporaryDirectory() as folder:
   t=Path(folder);helper=(ROOT/('ios/'+template+'/Cinematic.swift')).read_text();helper='\n'.join(l for l in helper.splitlines() if not l.startswith('import ')).replace('public ','')
   (t/'Cinematic.swift').write_text(helper)
   export=(a.source/'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift').read_text()
   rate_line=next(line.strip() for line in export.splitlines() if 'let rate = tuning[0]' in line)
   (t/'Rate.swift').write_text('import Foundation\nfunc exportRate(_ tuning: [Int])->Int { '+rate_line+'; return rate }\n@main struct Test {static func main() {for q in NagramiXRoundVideoSettings.Quality.allCases {for fps in [30,60] {for codec in [0,1] {precondition(exportRate([q.rawValue,fps,codec]) == q.bitRate)}}};print("PASS: 12 actual export bitrate configurations match capture model")}}')
   for opt in [[],['-O']]:
    for files in [[t/'Rate.swift'],[ROOT/('scripts/tests/NagramiXRoundPageSettingsTests.swift' if latest else 'scripts/tests/NagramiXRoundSheetSettingsTests.swift')],[ROOT/'scripts/tests/NagramiXCinematicSettingsTests.swift'],[t/'Cinematic.swift',ROOT/('scripts/tests/NagramiXCinematicPageCaptureBoundary.swift' if latest else 'scripts/tests/NagramiXCinematicCaptureBoundary.swift')]]:
     subprocess.run([str(a.swiftc),'-parse-as-library','-module-cache-path',str(t/'cache'),*opt,str(ROOT/('ios/'+template+'/Settings.swift')),*map(str,files),'-o',str(t/'test')],check=True);subprocess.run([str(t/'test')],check=True)
   subprocess.run([str(a.swiftc),'-frontend','-parse',*[str(a.source/n) for n in list(v['inputs'])+list(v['copies'])]],check=True)
 print('PASS: sheet/capture exact SHA, native parse and selected Swift tests; SDK/device pending')
if __name__=='__main__':main()
