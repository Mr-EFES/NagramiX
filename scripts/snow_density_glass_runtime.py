"""Полный действующий density node и glass control с явной границей UIKit."""
from pathlib import Path
from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1]
ITEM='submodules/SettingsUI/Sources/NagramiXSnowDensityItem.swift'
SETTINGS='submodules/NagramiXCore/Sources/NagramiXSnowSettings.swift'
LEGACY='submodules/LegacyComponents/Sources/TGPhotoEditorSliderView.m'
SWITCH='submodules/ItemListUI/Sources/Items/ItemListSwitchItem.swift'

def production(source):
    code=(source/ITEM).read_text()
    return '\n'.join(block(code,marker) for marker in [
        'class NagramiXSnowDensityItemNode:',
        'private struct NagramiXSnowDensityGeometry {',
        'private final class NagramiXSnowDensityGlassThumbView:',
        'private final class NagramiXSnowDensitySliderView:',
    ])

def fixture(source):
    text=production(source).replace('private ','fileprivate ').replace('@objc ','').replace('#selector(self.sliderValueChanged)','"sliderValueChanged"').replace('if #available(iOS 26.0, *)','if fixtureGlassAvailable')
    settings='enum NagramiXSnowSettings {\n'+block((source/SETTINGS).read_text(),'    public static func normalizedDensity(')+'\n}'
    legacy=(source/LEGACY).read_text()
    line=next(x.strip() for x in legacy.splitlines() if x.strip().startswith('CGFloat position = totalLength / (_maximumValue'))
    expression=line.split(' = ',1)[1].rstrip(';').replace('_minimumValue','minimum').replace('_maximumValue','maximum').replace('ABS(','abs(')
    native='func nativePositiveMinimumPosition(value:CGFloat,totalLength:CGFloat,minimum:CGFloat,maximum:CGFloat)->CGFloat{return '+expression+'}\n'
    return (ROOT/'scripts/tests/NagramiXSnowDensityGlassBoundary.swift').read_text()+'\n'+native+settings+'\n'+text+'\n'+(ROOT/'scripts/tests/NagramiXSnowDensityGlassTests.swift').read_text()
