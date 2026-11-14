"""Реальный проход V2/spacing и file branches; явные границы UIKit/моделей."""
from pathlib import Path
from validate_quick_format import block

ROOT=Path(__file__).resolve().parents[1]
LAYOUT='submodules/InstantPageUI/Sources/InstantPageV2Layout.swift'
HOST='submodules/TelegramUI/Components/Chat/ChatMessageRichDataBubbleContentNode/Sources/ChatMessageRichDataBubbleContentNode.swift'
PREVIEW='submodules/TelegramUI/Sources/Chat/ChatSendMessageRichTextPreview.swift'
SPACING='submodules/InstantPageUI/Sources/InstantPageLayoutSpacings.swift'
METRICS='submodules/InstantPageUI/Sources/InstantPageMetrics.swift'

def fixture(source):
    layout=(source/LAYOUT).read_text();spacing=(source/SPACING).read_text()
    parts=[(ROOT/'scripts/tests/NagramiXRichFilePaddingBoundary.swift').read_text()]
    for path,names in [
        ('submodules/InstantPageUI/Sources/InstantPageShapeItem.swift',['instantPageBulletMarkerDiameter','instantPageListItemTextwardOffset']),
        ('submodules/InstantPageUI/Sources/InstantPageV2ButtonRowLayout.swift',['instantPageBlockButtonHeight','instantPageBlockButtonSpacing']),
        (LAYOUT,['instantPageV2NumberMarkerTextwardOffset']),
    ]:
        for name in names:
            parts.append(next(line for line in (source/path).read_text().splitlines() if line.startswith('let '+name+':')))
    parts += [block(spacing,'enum BlockSequenceKind {'),block(spacing,'struct InstantPageBlockSpacing {'),
              'let instantPageBaseBlockSpacing: CGFloat = 8.0',
              'private let instantPageUnsupportedBlockSpacing = InstantPageBlockSpacing(verticalPadding: 8.0)',
              block((source/METRICS).read_text(),'struct InstantPageMetrics {'),
              block(spacing,'extension InstantPageBlock {'),block(spacing,'func spacingBetweenBlocks('),
              block(spacing,'public func instantPageV2ContentStartsFlushAtTop(').replace('public func','func',1),
              block((source/HOST).read_text(),'private func nagramiXRichFileHeaderSpacing(')]
    # Exact row layout branches, including media lookup/index/caption placement.
    audio=layout[layout.index('    case let .audio(audioId, caption):'):layout.index('    case let .webEmbed(url,',layout.index('    case let .audio(audioId, caption):'))]
    document=layout[layout.index('    case let .document(documentId, caption):'):layout.index('    case .unsupported:',layout.index('    case let .document(documentId, caption):'))]
    parts.append('''private func layoutBlock(_ block: InstantPageBlock, boundingWidth:CGFloat, horizontalInset:CGFloat, kind:BlockSequenceKind, isCover:Bool, previousItems:[InstantPageV2LaidOutItem], isLast:Bool, pathPrefix:[Int], context:inout LayoutContext)->[InstantPageV2LaidOutItem] {
switch block {
'''+audio+document+'''
case .anchor: return []
case .paragraph: return [.text(CGRect(x:horizontalInset,y:0,width:boundingWidth-2*horizontalInset,height:24))]
case .image: return [.text(CGRect(x:0,y:0,width:boundingWidth,height:120))]
default: return [.text(CGRect(x:horizontalInset,y:0,width:boundingWidth-2*horizontalInset,height:30))]
}}
''')
    driver=block(layout,'private func layoutBlockSequence(')
    parts.append(driver)
    previous=(ROOT/'ios/rich_file_padding/Before0.inc').read_text()
    parts.append(block(previous,'private func layoutBlockSequence(').replace('private func layoutBlockSequence(','private func originalSequence(',1))
    parts.append((ROOT/'scripts/tests/NagramiXRichFilePaddingTests.swift').read_text())
    return '\n'.join(parts)
