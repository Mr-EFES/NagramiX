#!/usr/bin/env python3
"""Проверить оформление, реальные битрейты и раздел Cinematic30."""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path
from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1]
UI='submodules/SettingsUI/Sources/NagramiXRoundQualityController.swift'
MODEL='submodules/NagramiXMediaSettings/Sources/NagramiXRoundVideoSettings.swift'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--swiftc',type=Path)
    a=p.parse_args()
    from validate_round_video_bitrate import delegate_if_applied
    if delegate_if_applied(a): return
    plan=json.loads((ROOT/'ios/round_video_refinement_patches.json').read_text())
    for name,digest in {**plan['guards'],**plan['outputs']}.items():
        assert hashlib.sha256((a.source/name).read_bytes()).hexdigest()==digest,name
    for name,digest in plan['templates'].items():
        assert hashlib.sha256((ROOT/'ios'/name).read_bytes()).hexdigest()==digest,name
    ui=(a.source/UI).read_text()
    assert 'self.statusBar.statusBarStyle = self.presentationData.theme.rootController.statusBarStyle.style' in ui
    assert 'content.textProperties.font = Font.regular(self.presentationData.listsFontSize.itemListBaseHeaderFontSize)' in ui
    assert 'content.textProperties.color = self.presentationData.theme.list.sectionHeaderTextColor' in ui
    assert 'indexPath.row == 0 ? "Да" : "Нет"' in ui
    assert all(s not in ui for s in ['reloadData(', 'reloadRows(', 'UIAlertController(', 'UIFont.preferredFont'])
    assert 'self.showsCinematic ? 4 : 3' in ui
    assert 'value.frameRate == .standard && self.supports(value)' in ui
    assert 'value.cinematic = false' in ui
    assert (a.source/MODEL).read_bytes()==(a.source/'submodules/Camera/Sources/NagramiXRoundVideoSettings.swift').read_bytes()
    presentation=(a.source/'submodules/TelegramPresentationData/Sources/PresentationData.swift').read_text()
    declaration=block(presentation,'public final class PresentationData:')
    fontFields=re.findall(r'public let (\w+): PresentationFontSize',declaration)
    used=re.findall(r'self.presentationData.(\w+).itemListBase\w+',ui)
    assert len(used)==3 and all(field in fontFields for field in used),(used,fontFields)
    print('PASS: all UI font accesses resolve to actual native PresentationData stored properties')
    print('PASS: exact source, stock status/header/row style, gated Cinematic30/Yes-No, mirrored camera/settings models')
    if a.swiftc:
        with tempfile.TemporaryDirectory() as folder:
            t=Path(folder)
            fontEnum=block((a.source/'submodules/TelegramUIPreferences/Sources/PresentationThemeSettings.swift').read_text(),'public enum PresentationFontSize:')
            fontExtension=block((a.source/'submodules/ItemListUI/Sources/ItemListItem.swift').read_text(),'public extension PresentationFontSize {')
            fields='\n'.join('let '+name+': PresentationFontSize' for name in fontFields)
            expressions=[line.split(' = ',1)[1].strip().replace('self.presentationData','data') for line in ui.splitlines() if ' = Font.regular(' in line]
            assert len(expressions)==3
            fonts='import Foundation\n'+fontEnum+'\n'+fontExtension+'\nstruct PresentationData {\n'+fields+'\n}\nenum Font {static func regular(_ value:CGFloat)->CGFloat {value}}\nfunc fonts(_ data:PresentationData)->[CGFloat] {['+','.join(expressions)+']}\n'
            fonts+='for (size,base) in zip(PresentationFontSize.allCases,[14.0,15.0,17.0,19.0,23.0,26.0,16.0]) {let values=fonts(PresentationData(chatFontSize:.extraLargeX2,listsFontSize:size));precondition(values == [floor(base*13/17),base,floor(base*15/17)])}\nprint("PASS: 21 actual font expressions against native PresentationData fields/enum/list sizes")\n'
            fontFile=t/'Fonts.swift';fontFile.write_text(fonts)
            subprocess.run([str(a.swiftc),'-warnings-as-errors','-module-cache-path',str(t/'cache'),str(fontFile),'-o',str(t/'fonts')],check=True)
            subprocess.run([str(t/'fonts')],check=True)
            old=t/'OldFonts.swift';old.write_text(fonts.replace('data.listsFontSize.','data.fontSize.'))
            failure=subprocess.run([str(a.swiftc),'-module-cache-path',str(t/'cache'),'-typecheck',str(old)],capture_output=True)
            assert failure.returncode!=0 and b"no member 'fontSize'" in failure.stderr,failure.stderr.decode(errors='replace')
            print('PASS: pre-fix native PresentationData.fontSize compile regression rejected')
            model=a.source/MODEL
            rate=(a.source/'submodules/TelegramUI/Components/MediaEditor/Sources/MediaEditorValues.swift').read_text()
            line=next(l.strip() for l in rate.splitlines() if 'let rate = tuning[0]' in l)
            recorder=(a.source/'submodules/Camera/CameraNeo/Sources/VideoRecorder.swift').read_text()
            capture=next(l.strip() for l in recorder.splitlines() if 'AVVideoAverageBitRateKey: self.processor.quality' in l).split(': ',1)[1].rstrip(',')
            rateSource=t/'Rate.swift'
            rateSource.write_text('import Foundation\nstruct Processor {let quality:NagramiXRoundVideoSettings?}\nstruct Capture {let processor:Processor;func rate()->Int {'+'return '+capture+'}}\nfunc captureBitRate(_ quality:NagramiXRoundVideoSettings?)->Int {Capture(processor:Processor(quality:quality)).rate()}\nfunc exportRate(_ tuning:[Int])->Int {'+line+';return rate}')
            methods=['private func supports(', 'private func shouldShowCinematic(', 'private func enabled(', 'private func commit(',
                     'func numberOfSections(', 'func tableView(_ tableView: UITableView, didSelectRowAt']
            page=t/'Page.swift';page.write_text((ROOT/'scripts/tests/NagramiXRoundRefinementBoundary.swift').read_text().replace('// PAGE_METHODS','\n'.join(block(ui,m).replace('private func','func') for m in methods)))
            cinematic=t/'Cinematic.swift'
            text=(ROOT/'ios/round_video_refinement/Cinematic.swift').read_text()
            cinematic.write_text('\n'.join(l for l in text.splitlines() if not l.startswith('import ')).replace('public ',''))
            # Та же проверка форматов с новым требованием30, старые аппаратные gates сохранены.
            boundary=(ROOT/'scripts/tests/NagramiXCinematicPageCaptureBoundary.swift').read_text()
            boundary=boundary.replace('let expected = format.isCinematicVideoCaptureSupported','let expected = fps == .standard && format.isCinematicVideoCaptureSupported')
            boundary=boundary.replace('frameRate: .smooth, cinematic: true','frameRate: .standard, cinematic: true')
            boundary=boundary.replace('.back: .init([.init(fps: 30)])', '.back: .init([.init(supported: false)])')
            caps=t/'Capture.swift';caps.write_text(boundary)
            for opt in [[],['-O']]:
                for files in [
                    [rateSource, ROOT/'scripts/tests/NagramiXRoundRefinementSettingsTests.swift'],
                    [page,ROOT/'scripts/tests/NagramiXRoundRefinementPageTests.swift'],
                    [cinematic,caps],
                ]:
                    subprocess.run([str(a.swiftc),'-parse-as-library','-warnings-as-errors','-module-cache-path',str(t/'cache'),*opt,str(model),*map(str,files),'-o',str(t/'test')],check=True)
                    subprocess.run([str(t/'test')],check=True,env={**os.environ,'XDG_CONFIG_HOME':str(t/'prefs')})
            subprocess.run([str(a.swiftc),'-frontend','-parse',*[str(a.source/n) for n in plan['outputs']]],check=True)
    print('PASS: round refinement; UIKit/Apple SDK/real camera pending')

if __name__=='__main__':main()
