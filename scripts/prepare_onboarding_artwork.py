#!/usr/bin/env python3
"""Export seven uniformly padded assets from the selected original RGBA masters.

The attached white JPEG previews match these earlier transparent originals.
Keep the original pixels/alpha; only crop in the sheet's actual whitespace and
resize proportionally for a shared visible size. No redraw or recoloring.
Requires Pillow; offline resource packaging, never run by the iOS application.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / 'ios/branding/OnboardingMasters'
DEST = ROOT / 'ios/Resources/Onboarding'
SIZE = 1024
VISIBLE_SIDE = 800
SCENES = [
    ('Logo', 'Logo.png', (0, 0, 1254, 1254)),
    ('Communication', 'Sheet.png', (0, 0, 532, 540)),
    ('Free', 'Sheet.png', (532, 0, 999, 540)),
    ('Personal', 'Sheet.png', (999, 0, 1536, 540)),
    ('Privacy', 'Sheet.png', (0, 540, 524, 1024)),
    ('Nearby', 'Sheet.png', (524, 540, 1018, 1024)),
    ('Phone', 'Phone.png', (0, 0, 1254, 1254)),
]

# Very small fragments of adjacent scenes extend into the whitespace gutter.
# These coordinates are relative to the crop and do not cover the scene itself.
GUTTER_EXCLUSIONS = {
    'Free': [(456, 430, 467, 490)],
    'Personal': [(0, 170, 8, 225)],
    'Nearby': [(0, 100, 8, 210)],
}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {}
    provenance = {'method': 'Original transparent masters matching selected JPEG previews; whitespace crop with removal of tiny adjacent-cell gutter fragments, proportional resize, transparent padding. No redraw, recolor or alpha matte replacement.', 'canvas': SIZE, 'visibleLongestSide': VISIBLE_SIDE, 'scenes': []}
    for name, filename, crop in SCENES:
        source = MASTER / filename
        with Image.open(source) as im:
            expected = (1254, 1254) if filename in ('Logo.png', 'Phone.png') else (1536, 1024)
            if im.size != expected or im.mode != 'RGBA':
                raise SystemExit(f'Unexpected master: {filename}: {im.size}/{im.mode}')
            art = im.crop(crop)
        for excluded in GUTTER_EXCLUSIONS.get(name, []):
            art.paste((0, 0, 0, 0), excluded)
        bbox = art.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()
        if bbox is None:
            raise SystemExit(f'Empty illustration: {name}')
        scale = VISIBLE_SIDE / max(bbox[2] - bbox[0], bbox[3] - bbox[1])
        resized = art.resize((round(art.width * scale), round(art.height * scale)), Image.Resampling.LANCZOS)
        canvas_height = 864 if name == 'Phone' else SIZE
        position = (round(SIZE / 2 - (bbox[0] + bbox[2]) / 2 * scale), round(canvas_height / 2 - (bbox[1] + bbox[3]) / 2 * scale))
        canvas = Image.new('RGBA', (SIZE, canvas_height))
        canvas.alpha_composite(resized, position)
        target = DEST / f'NagramiXOnboarding{name}.png'
        canvas.save(target, optimize=True)
        manifest[target.name] = {'source': str(target.relative_to(ROOT / 'ios')), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
        provenance['scenes'].append({'name': name, 'canvas': [SIZE, canvas_height], 'master': filename, 'masterSha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'crop': crop, 'sourceVisibleBounds': bbox, 'scale': scale, 'excludedAdjacentFragments': GUTTER_EXCLUSIONS.get(name, []), 'output': target.name})
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (MASTER / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(f'Prepared {len(manifest)} original illustrations: width {SIZE}, phone aspect-fit canvas, visible longest side {VISIBLE_SIDE}px.')


if __name__ == '__main__':
    main()
